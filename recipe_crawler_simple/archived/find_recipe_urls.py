from datetime import datetime
import logging
import random
import warnings

from bs4 import BeautifulSoup
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from config import setup_logging
from utils import fetch_sitemap_with_fallback, is_valid_url
from db import RecipeUrl, Sitemap, RecipeSite, get_db_session

# Suppress insecure request warnings
warnings.simplefilter("ignore", InsecureRequestWarning)

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)


def extract_urls(sitemap_content):
    """Extract URLs and nested sitemap URLs from the sitemap content."""
    soup = BeautifulSoup(sitemap_content, "lxml-xml")
    urls_data = []
    
    # Check for sitemap index
    sitemapindex = soup.find("sitemapindex")
    if sitemapindex:
        for sitemap in sitemapindex.find_all("sitemap"):
            loc = sitemap.find("loc")
            lastmod = sitemap.find("lastmod")
            if loc:
                urls_data.append({
                    "url": loc.text,
                    "lastmod": lastmod.text if lastmod else None
                })
    else:
        urlset = soup.find("urlset")
        if urlset:
            for url_entry in urlset.find_all("url"):
                loc = url_entry.find("loc")
                lastmod = url_entry.find("lastmod")
                if loc:
                    urls_data.append({
                        "url": loc.text,
                        "lastmod": lastmod.text if lastmod else None
                    })
        else:
            for loc in soup.find_all("loc"):
                lastmod = loc.find_next_sibling("lastmod")
                urls_data.append({
                    "url": loc.text,
                    "lastmod": lastmod.text if lastmod else None
                })

    sitemap_urls = [data["url"] for data in urls_data if "sitemap" in data["url"].lower()]
    regular_urls_data = [data for data in urls_data if "sitemap" not in data["url"].lower()]
    
    return sitemap_urls, regular_urls_data


def save_urls_to_db(session, urls_data, sitemap_obj, batch_size=1000):
    """Save new valid URLs to the database using batching."""
    total_added = 0
    
    # Process URLs in batches
    for i in range(0, len(urls_data), batch_size):
        batch = urls_data[i:i+batch_size]
        urls_to_check = [url_data["url"].lower().rstrip('/') for url_data in batch]
        
        # Find which URLs in this batch already exist
        query = session.query(RecipeUrl.url).filter(
            RecipeUrl.url.in_([url for url in urls_to_check])
        )
        existing_urls = {url[0].lower().rstrip('/') for url in query}
        
        urls_to_add = []
        for url_data in batch:
            url = url_data["url"].lower().rstrip('/')
            
            # Skip if already exists
            if url in existing_urls:
                continue
            
            # Add if valid
            if is_valid_url(url):
                urls_to_add.append(RecipeUrl(
                    url=url,
                    sitemap_id=sitemap_obj.id,
                    last_modified=url_data["lastmod"],
                    last_extracted=datetime.datetime.utcnow(),
                    randnum=random.randint(0, 10)
                ))
        
        if urls_to_add:
            try:
                session.add_all(urls_to_add)
                session.commit()
                total_added += len(urls_to_add)
                logging.info(f"Added {len(urls_to_add)} URLs from batch")
            except Exception as e:
                session.rollback()
                logging.warning(f"Error saving URLs batch: {e}")

    logging.info(f"Total URLs added: {total_added}")
    return total_added


def process_sitemaps(site_obj, session, max_depth=3):
    """Process all sitemaps for a site and extract URLs with a maximum depth limit."""
    base_url = site_obj.recipe_site_url
    logging.info(f"Processing sitemaps for: {base_url}")
    
    # Collect sitemaps to process
    sitemaps_to_process = []
    
    # Add manual sitemaps if available
    if site_obj.manual_sitemaps:
        for sitemap in site_obj.manual_sitemaps.split(','):
            sitemaps_to_process.append((sitemap, 0))  # (url, depth)
    
    # Add standard sitemap locations
    for sitemap in [
        f"{base_url.rstrip('/')}/sitemap.xml",
        f"{base_url.rstrip('/')}/sitemap_index.xml",
        f"{base_url.rstrip('/')}/sitemap",
        f"{base_url.rstrip('/')}/sitemaps.xml",
    ]:
        sitemaps_to_process.append((sitemap, 0))

    processed_sitemaps = set()

    while sitemaps_to_process:
        sitemap_tuple = sitemaps_to_process.pop(0)  # Get the first item
        sitemap_url, current_depth = sitemap_tuple
        
        if sitemap_url in processed_sitemaps:
            continue
            
        if current_depth > max_depth:
            logging.info(f"Skipping sitemap at depth {current_depth}: {sitemap_url}")
            continue

        logging.info(f"Processing sitemap: {sitemap_url} (depth: {current_depth})")
        sitemap_content = fetch_sitemap_with_fallback(sitemap_url)
        
        if not sitemap_content:
            continue
            
        # Extract URLs from sitemap
        sitemap_urls, regular_urls_data = extract_urls(sitemap_content)
        
        # Save or get sitemap record
        sitemap_obj = session.query(Sitemap).filter_by(sitemap_url=sitemap_url, site_id=site_obj.id).first()
        if not sitemap_obj:
            sitemap_obj = Sitemap(sitemap_url=sitemap_url, site_id=site_obj.id)
            session.add(sitemap_obj)
            session.commit()
            
        # Save the URLs
        save_urls_to_db(session, regular_urls_data, sitemap_obj)
        
        # Add nested sitemaps with incremented depth
        for nested_sitemap in sitemap_urls:
            sitemaps_to_process.append((nested_sitemap, current_depth + 1))
            
        processed_sitemaps.add(sitemap_url)


def update_recipe_sites():
    """Process sites that need URL extraction."""
    logging.info("Starting recipe site processing")
    
    session = get_db_session() # Create a session object.
    
    try:
        while True:
            # Find next site to process
            site = session.query(RecipeSite).filter(
                RecipeSite.status.notin_(["extraction_in_progress", "extraction_complete"])
            ).first()
            
            if not site:
                break
                
            # Mark as in progress
            site.status = "extraction_in_progress"
            session.commit()
            
            try:
                process_sitemaps(site, session)
                
                # Mark complete
                site.last_processed = datetime.utcnow()
                site.status = "extraction_complete"
                session.commit()
                
            except Exception as e:
                logging.error(f"Error processing {site.recipe_site_url}: {e}")
                site.status = "extraction_failed"
                site.last_processed = datetime.utcnow()
                session.commit()
                
    finally:
        session.close()


if __name__ == "__main__":
    try:
        update_recipe_sites()
        logging.info("Processing completed successfully")
    except Exception as e:
        logging.error(f"Script failed: {e}")
        exit(1)