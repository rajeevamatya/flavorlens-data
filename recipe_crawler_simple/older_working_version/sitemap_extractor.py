import logging
import random
import argparse
from datetime import datetime
from bs4 import BeautifulSoup
import warnings
import psycopg2
from psycopg2.extras import execute_values

from config import setup_logging, get_db_connection
from utils import fetch_sitemap_with_fallback, is_valid_url
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Suppress insecure request warnings
warnings.simplefilter("ignore", InsecureRequestWarning)

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)



def get_sitemaps_and_urls(site_url, manual_sitemaps=None, max_depth=3):
    """
    Get all sitemaps and URLs from a recipe site
    
    Args:
        site_url (str): The URL of the recipe site
        manual_sitemaps (str, optional): Comma-separated list of manual sitemap URLs
        max_depth (int, optional): Maximum depth to crawl nested sitemaps
        
    Returns:
        dict: Dictionary with sitemaps as keys and lists of URLs as values
    """
    sitemaps_to_process = []
    processed_sitemaps = set()
    sitemap_url_dict = {}
    
    # Collect initial sitemaps
    if manual_sitemaps:
        for sitemap in manual_sitemaps.split(','):
            sitemaps_to_process.append((sitemap.strip(), 0))
    
    # Add standard sitemap locations
    base_url = site_url.rstrip('/')
    standard_locations = [
        f"{base_url}/sitemap.xml",
        f"{base_url}/sitemap_index.xml",
        f"{base_url}/sitemap",
        f"{base_url}/sitemaps.xml",
    ]
    
    for sitemap in standard_locations:
        sitemaps_to_process.append((sitemap, 0))
    
    # Process sitemaps up to max depth
    while sitemaps_to_process:
        sitemap_url, depth = sitemaps_to_process.pop(0)
        
        if sitemap_url in processed_sitemaps or depth > max_depth:
            continue
        
        logger.info(f"Processing sitemap: {sitemap_url} (depth: {depth})")
        
        try:
            sitemap_content = fetch_sitemap_with_fallback(sitemap_url)
            
            if not sitemap_content:
                logger.warning(f"No content found for sitemap: {sitemap_url}")
                processed_sitemaps.add(sitemap_url)
                continue
            
            # Extract URLs and nested sitemaps
            nested_sitemaps, urls = extract_from_sitemap(sitemap_content)
            
            # Store URLs for this sitemap
            sitemap_url_dict[sitemap_url] = urls
            
            # Add nested sitemaps to processing queue
            for nested_url in nested_sitemaps:
                sitemaps_to_process.append((nested_url, depth + 1))
            
        except Exception as e:
            # Just log the error and continue with other sitemaps
            logger.error(f"Failed to process sitemap {sitemap_url}: {e}")
        
        processed_sitemaps.add(sitemap_url)
    
    logger.info(f"Processed {len(sitemap_url_dict)} sitemaps for {site_url}")
    return sitemap_url_dict


def extract_from_sitemap(sitemap_content):
    """
    Extract URLs and nested sitemaps from sitemap content
    
    Args:
        sitemap_content (str): XML content of the sitemap
        
    Returns:
        tuple: (list of nested sitemap URLs, list of URL data dictionaries)
    """
    soup = BeautifulSoup(sitemap_content, "lxml-xml")
    urls_data = []
    nested_sitemaps = []
    
    # Check for sitemap index
    sitemapindex = soup.find("sitemapindex")
    if sitemapindex:
        for sitemap in sitemapindex.find_all("sitemap"):
            loc = sitemap.find("loc")
            if loc:
                nested_sitemaps.append(loc.text)
    else:
        # Process URL set
        urlset = soup.find("urlset")
        if urlset:
            for url_entry in urlset.find_all("url"):
                loc = url_entry.find("loc")
                lastmod = url_entry.find("lastmod")
                if loc:
                    url = loc.text
                    if "sitemap" in url.lower():
                        nested_sitemaps.append(url)
                    else:
                        urls_data.append({
                            "url": url,
                            "lastmod": lastmod.text if lastmod else None
                        })
        else:
            # Fallback for non-standard sitemaps
            for loc in soup.find_all("loc"):
                url = loc.text
                lastmod = loc.find_next_sibling("lastmod")
                if "sitemap" in url.lower():
                    nested_sitemaps.append(url)
                else:
                    urls_data.append({
                        "url": url,
                        "lastmod": lastmod.text if lastmod else None
                    })
    
    return nested_sitemaps, urls_data


def save_urls_to_db(sitemap_url_dict, site_id):
    """
    Save URLs directly to recipe_urls table with sitemap URL as a field
    
    Args:
        sitemap_url_dict (dict): Dictionary with sitemaps as keys and lists of URLs as values
        site_id (int): The database ID of the site
        
    Returns:
        dict: Statistics about the operation
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {
        "sitemaps_processed": 0,
        "urls_found": 0,
        "urls_added": 0,
        "urls_skipped": 0
    }
    
    try:
        # Process each sitemap
        for sitemap_url, urls_data in sitemap_url_dict.items():
            stats["sitemaps_processed"] += 1
            stats["urls_found"] += len(urls_data)
            
            # Get existing URLs to avoid duplicates
            normalized_urls = [url_data["url"].lower().rstrip('/') for url_data in urls_data]
            
            if normalized_urls:
                placeholders = ','.join(['%s'] * len(normalized_urls))
                cursor.execute(
                    f"SELECT LOWER(url) FROM recipe_urls WHERE LOWER(url) IN ({placeholders})",
                    normalized_urls
                )
                existing_urls = {row[0] for row in cursor.fetchall()}
            else:
                existing_urls = set()
            
            # Prepare URLs to add
            current_time = datetime.utcnow()
            urls_to_add = []
            
            for url_data in urls_data:
                norm_url = url_data["url"].lower().rstrip('/')
                if norm_url not in existing_urls and is_valid_url(norm_url):
                    urls_to_add.append((
                        norm_url,
                        site_id,
                        sitemap_url,  # Store sitemap URL directly with the recipe URL
                        url_data["lastmod"],
                        current_time,
                        random.randint(0, 10)
                    ))
            
            # Save all URLs for this sitemap in one go
            if urls_to_add:
                execute_values(
                    cursor,
                    "INSERT INTO recipe_urls (url, site_id, sitemap_url, last_modified, last_extracted, randnum) VALUES %s",
                    urls_to_add
                )
                conn.commit()
                stats["urls_added"] += len(urls_to_add)
                stats["urls_skipped"] += len(urls_data) - len(urls_to_add)
            else:
                stats["urls_skipped"] += len(urls_data)
        
        # Update site status to indicate URL extraction is complete
        cursor.execute(
            "UPDATE recipe_sites SET last_processed = %s, status = %s WHERE id = %s",
            (datetime.utcnow(), "url_extraction_complete", site_id)
        )
        conn.commit()
        
    except Exception as e:
        logger.error(f"Error saving URLs: {e}")
        conn.rollback()
        
        # Mark site as failed
        cursor.execute(
            "UPDATE recipe_sites SET status = %s, last_processed = %s WHERE id = %s",
            ("url_extraction_failed", datetime.utcnow(), site_id)
        )
        conn.commit()
        
    finally:
        cursor.close()
        conn.close()
    
    return stats


def crawl_site_for_urls(site_url, site_id=None, manual_sitemaps=None):
    """
    Crawl a recipe site to extract URLs from sitemaps
    
    Args:
        site_url (str): The URL of the recipe site
        site_id (int, optional): The database ID of the site
        manual_sitemaps (str, optional): Comma-separated list of manual sitemap URLs
        
    Returns:
        dict: Statistics about the crawling operation
    """
    logger.info(f"Starting to extract URLs from site: {site_url}")
    
    # Get site from database if site_id not provided
    if not site_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, manual_sitemaps FROM recipe_sites WHERE recipe_site_url = %s",
            (site_url,)
        )
        site_result = cursor.fetchone()
        
        if site_result:
            site_id = site_result[0]
            manual_sitemaps = site_result[1]
            cursor.execute(
                "UPDATE recipe_sites SET status = %s WHERE id = %s",
                ("url_extraction_in_progress", site_id)
            )
            conn.commit()
        
        cursor.close()
        conn.close()
    
    # Step 1: Get all sitemaps and URLs
    sitemap_url_dict = get_sitemaps_and_urls(site_url, manual_sitemaps)
    
    # Step 2: Save URLs to database
    stats = save_urls_to_db(sitemap_url_dict, site_id)
    
    logger.info(f"Completed URL extraction for site: {site_url}")
    logger.info(f"Stats: {stats}")
    
    return stats


def extract_all_site_urls():
    """Extract URLs from all recipe sites that need processing"""
    logger.info("Starting recipe site URL extraction")
    
    try:
        # Get sites to process
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, recipe_site_url, manual_sitemaps FROM recipe_sites
            WHERE status = 'url_extraction_pending' OR last_processed < (CURRENT_TIMESTAMP - INTERVAL '1 month')"""
        )
        sites = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for site_id, recipe_site_url, manual_sitemaps in sites:
            crawl_site_for_urls(recipe_site_url, site_id, manual_sitemaps)
            
        logger.info("URL extraction completed for all sites")
        
    except Exception as e:
        logger.error(f"URL extraction failed: {e}")
        raise


if __name__ == "__main__":
        extract_all_site_urls()