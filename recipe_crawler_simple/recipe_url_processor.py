import logging
import asyncio
import argparse
import psycopg2
import psycopg2.extras
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from config import setup_logging, get_db_connection
from utils import fetch_with_proxies, is_recipe

setup_logging()
logger = logging.getLogger(__name__)


class ContentProcessor:
    def __init__(self, batch_size=128, max_concurrency=16):
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(max_concurrency)

    def get_pending_urls(self):
        """Get batch of pending URLs from database"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    "SELECT id, url FROM recipe.recipe_urls WHERE crawl_status = 'pending' LIMIT %s",
                    (self.batch_size,)
                )
                return cursor.fetchall()

    async def process_url(self, url_data):
        """Process a single URL"""
        url_id, url = url_data['id'], url_data['url']
        
        async with self.semaphore:
            try:
                # Fetch and parse content
                content, proxy_used = await fetch_with_proxies(url)
                if not content:
                    return url_id, None, "fetch_failed", proxy_used
                
                soup = BeautifulSoup(content, "lxml")
                
                # Remove unnecessary elements and extract text
                for tag in soup.find_all(["nav", "footer", "aside", "script", "style", "img"]):
                    tag.decompose()
                
                clean_text = soup.get_text(separator="\n", strip=True)
                title = soup.title.string.strip() if soup.title else ""
                
                # Get description from meta tags
                description = ""
                for meta in soup.find_all("meta"):
                    if meta.get("name") == "description" or meta.get("property") == "og:description":
                        description = meta.get("content", "").strip()
                        break
                
                # Check if it's a recipe
                recipe_flag = is_recipe(url, title, description, clean_text)
                
                return url_id, {
                    'parsed_text': clean_text,
                    'page_title': title,
                    'page_description': description,
                    'is_recipe': recipe_flag,
                    'proxy_used': proxy_used
                }, None, proxy_used
                
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                return url_id, None, str(e), None

    def save_results(self, results):
        """Save processing results to database"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for result in results:
                    if len(result) == 4:
                        url_id, data, error, proxy_used = result
                    else:
                        # Handle backward compatibility if needed
                        url_id, data, error = result
                        proxy_used = None
                    
                    if data:
                        # Success case
                        cursor.execute(
                            """UPDATE recipe.recipe_urls 
                               SET parsed_text = %s, page_title = %s, page_description = %s,
                                   is_recipe = %s, crawl_status = 'complete', 
                                   proxy_used = %s, last_crawled = %s
                               WHERE id = %s""",
                            (data['parsed_text'], data['page_title'], data['page_description'],
                             data['is_recipe'], data.get('proxy_used'), datetime.utcnow(), url_id)
                        )
                    else:
                        # Failure case
                        cursor.execute(
                            """UPDATE recipe.recipe_urls 
                               SET crwal_status = 'failed', crawl_failure_reason = %s, 
                                   proxy_used = %s, last_crawled = %s
                               WHERE id = %s""",
                            (error, proxy_used, datetime.utcnow(), url_id)
                        )
                conn.commit()

    async def run(self):
        """Main processing loop"""
        logger.info("Starting content processor")
        
        while True:
            urls = self.get_pending_urls()
            
            if not urls:
                logger.info("No URLs to process, waiting...")
                await asyncio.sleep(5)
                continue
            
            logger.info(f"Processing {len(urls)} URLs")
            
            # Process URLs concurrently
            tasks = [self.process_url(url_data) for url_data in urls]
            results = await asyncio.gather(*tasks)
            
            # Save results
            self.save_results(results)
            
            successful = sum(1 for result in results if len(result) >= 2 and result[1])
            failed = len(results) - successful
            logger.info(f"Batch complete: {successful} successful, {failed} failed")

async def main():
    parser = argparse.ArgumentParser(description="Process recipe URLs")
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size")
    parser.add_argument("--max-concurrency", type=int, default=16, help="Max concurrency")
    args = parser.parse_args()
    
    processor = ContentProcessor(args.batch_size, args.max_concurrency)
    await processor.run()


if __name__ == "__main__":
    asyncio.run(main())