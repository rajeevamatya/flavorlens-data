import logging
import random
import argparse
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
import psycopg2
from psycopg2.extras import execute_values

from config import setup_logging, get_db_connection
from utils import fetch_sitemap_with_fallback, is_valid_url

setup_logging()
logger = logging.getLogger(__name__)


def normalize_url(url):
    """Comprehensive URL normalization"""
    if not url:
        return url
        
    try:
        parsed = urlparse(url.lower())
        # Force HTTPS
        scheme = 'https'
        # Remove trailing slash from path
        path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
        # Remove query parameters and fragments for normalization
        return urlunparse((scheme, parsed.netloc, path, '', '', ''))
    except:
        return url.lower().rstrip('/')


class SitemapCrawler:
    def __init__(self, max_depth=3):
        self.max_depth = max_depth
        self.processed_sitemaps = set()
        
    def get_all_urls_from_site(self, site_url, manual_sitemaps=None):
        """Get all URLs from a site's sitemaps"""
        all_urls = []
        sitemaps_to_process = []
        
        # Collect initial sitemaps
        if manual_sitemaps:
            # Handle manual_sitemaps as array from database
            if isinstance(manual_sitemaps, list):
                sitemaps_to_process.extend([s.strip() for s in manual_sitemaps])
            else:
                sitemaps_to_process.extend([s.strip() for s in manual_sitemaps.split(',')])
        
        # Add standard sitemap locations
        base_url = site_url.rstrip('/')
        standard_locations = [
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml", 
            f"{base_url}/sitemap",
            f"{base_url}/sitemaps.xml"
        ]
        sitemaps_to_process.extend(standard_locations)
        
        # Process sitemaps with depth tracking
        for sitemap_url in sitemaps_to_process:
            urls = self._process_sitemap_recursive(sitemap_url, 0)
            all_urls.extend(urls)
            
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url_data in all_urls:
            normalized = normalize_url(url_data['original_url'])
            if normalized not in seen:
                seen.add(normalized)
                url_data['url'] = normalized  # Add normalized URL
                unique_urls.append(url_data)
                
        logger.info(f"Found {len(unique_urls)} unique URLs from {len(self.processed_sitemaps)} sitemaps")
        return unique_urls
    
    def _process_sitemap_recursive(self, sitemap_url, depth):
        """Recursively process sitemaps up to max depth"""
        if sitemap_url in self.processed_sitemaps or depth > self.max_depth:
            return []
            
        logger.info(f"Processing sitemap: {sitemap_url} (depth: {depth})")
        
        try:
            content = fetch_sitemap_with_fallback(sitemap_url)
            if not content:
                return []
                
            nested_sitemaps, urls = self._extract_from_sitemap(content, sitemap_url)
            
            # Process nested sitemaps
            for nested_url in nested_sitemaps:
                urls.extend(self._process_sitemap_recursive(nested_url, depth + 1))
                
            self.processed_sitemaps.add(sitemap_url)
            return urls
            
        except Exception as e:
            logger.error(f"Failed to process sitemap {sitemap_url}: {e}")
            return []
    
    def _extract_from_sitemap(self, content, sitemap_url):
        """Extract URLs and nested sitemaps from sitemap content"""
        soup = BeautifulSoup(content, "lxml-xml")
        urls_data = []
        nested_sitemaps = []
        
        # Check for sitemap index
        if soup.find("sitemapindex"):
            for sitemap in soup.find_all("sitemap"):
                loc = sitemap.find("loc")
                if loc:
                    nested_sitemaps.append(loc.text)
        else:
            # Process URL entries
            for url_entry in soup.find_all("url"):
                loc = url_entry.find("loc")
                if loc:
                    url = loc.text
                    if "sitemap" in url.lower():
                        nested_sitemaps.append(url)
                    else:
                        lastmod = url_entry.find("lastmod")
                        urls_data.append({
                            "original_url": url,  # Store original URL
                            "lastmod": lastmod.text if lastmod else None,
                            "sitemap_url": sitemap_url
                        })
            
            # Fallback for non-standard sitemaps
            if not urls_data and not nested_sitemaps:
                for loc in soup.find_all("loc"):
                    url = loc.text
                    if "sitemap" in url.lower():
                        nested_sitemaps.append(url)
                    else:
                        urls_data.append({
                            "original_url": url,  # Store original URL
                            "lastmod": None,
                            "sitemap_url": sitemap_url
                        })
        
        return nested_sitemaps, urls_data


def save_urls_to_database(urls_data, site_id):
    """Save URLs to database with duplicate handling"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Filter valid URLs and prepare for insertion
            current_time = datetime.utcnow()
            urls_to_insert = []
            
            for url_data in urls_data:
                if is_valid_url(url_data['original_url']):
                    urls_to_insert.append((
                        url_data['original_url'],           # original_url
                        url_data['url'],                    # normalized url
                        site_id,
                        url_data['sitemap_url'],
                        random.randint(0, 10)
                    ))
            
            if urls_to_insert:
                # Use ON CONFLICT to handle duplicates on normalized URL
                execute_values(
                    cursor,
                    """INSERT INTO recipe.recipe_urls 
                       (original_url, url, site_id, sitemap_url, randnum) 
                       VALUES %s 
                       ON CONFLICT (url) DO NOTHING""",
                    urls_to_insert
                )
                
            # Update site status
            cursor.execute(
                """UPDATE recipe.recipe_sites 
                   SET last_processed = %s, status = 'complete' 
                   WHERE id = %s""",
                (datetime.utcnow(), site_id)
            )
            
            conn.commit()
            logger.info(f"Inserted {len(urls_to_insert)} URLs for site {site_id}")


def process_site(site_url, site_id=None, manual_sitemaps=None):
    """Process a single site to extract URLs"""
    logger.info(f"Starting URL extraction for: {site_url}")
    
    try:
        # Get site info if needed
        if not site_id:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, manual_sitemaps FROM recipe.recipe_sites WHERE url = %s",
                        (site_url,)
                    )
                    result = cursor.fetchone()
                    if result:
                        site_id, manual_sitemaps = result
        
        # Extract URLs from sitemaps
        crawler = SitemapCrawler()
        urls_data = crawler.get_all_urls_from_site(site_url, manual_sitemaps)
        
        # Save to database
        save_urls_to_database(urls_data, site_id)
        
        logger.info(f"Completed URL extraction for: {site_url}")
        
    except Exception as e:
        logger.error(f"Failed to process site {site_url}: {e}")
        # Mark site as failed
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """UPDATE recipe.recipe_sites 
                       SET status = 'failed', last_processed = %s 
                       WHERE id = %s""",
                    (datetime.utcnow(), site_id)
                )
                conn.commit()


def process_all_sites():
    """Process all sites that need URL extraction"""
    logger.info("Starting URL extraction for all sites")
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT id, url, manual_sitemaps 
                   FROM recipe.recipe_sites
                   WHERE status = 'pending' 
                   OR last_processed < (CURRENT_TIMESTAMP - INTERVAL '1 month')"""
            )
            sites = cursor.fetchall()
    
    for site_id, site_url, manual_sitemaps in sites:
        process_site(site_url, site_id, manual_sitemaps)
    
    logger.info("Completed URL extraction for all sites")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract URLs from recipe sites")
    parser.add_argument("--site-url", help="Single site URL to process")
    args = parser.parse_args()
    
    if args.site_url:
        process_site(args.site_url)
    else:
        process_all_sites()