import logging
import asyncio
import argparse
import warnings
import psycopg2
import psycopg2.extras
from datetime import datetime
from bs4 import BeautifulSoup
import html2text

from config import setup_logging, get_db_connection
from utils import is_recipe, fetch_with_proxies

# Suppress warnings
warnings.simplefilter("ignore")

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)
logger.info("Logging setup complete.")


class ContentProcessor:
    def __init__(self, batch_size=128, max_concurrency=16):
        """
        Initialize the content processor
        
        Args:
            batch_size (int): Number of URLs to process in each batch
            max_concurrency (int): Maximum concurrent URL processing
        """
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency
        self.total_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0
        }

    async def process_url_async(self, url_data):
        """
        Asynchronously process a single URL
        
        Args:
            url_data (dict): Dictionary containing URL ID and URL
        
        Returns:
            dict: Processing result
        """
        url_id, url = url_data['id'], url_data['url']
        logger.info(f"Processing URL: {url}")
        
        result = {
            'url_id': url_id,
            'success': False,
            'is_recipe': False,
            'data': {},
            'failure_reason': None
        }
        
        try:
            # Fetch content
            content, proxy_used = await fetch_with_proxies(url)
            if not content:
                result['failure_reason'] = "no_response_after_all_retries"
                return result
            
            # Parse content
            soup = BeautifulSoup(content, "lxml")
            
            # Remove unnecessary elements
            for tag in soup.find_all(["nav", "footer", "aside", "script", "style", "img"]):
                tag.decompose()
            
            # Extract text
            text = soup.get_text(separator="\n").strip()
            clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
            
            # Convert to markdown
            h2t = html2text.HTML2Text()
            h2t.ignore_links = True
            h2t.ignore_images = True
            markdown = h2t.handle(content)
            
            # Extract metadata
            title = soup.title.string.strip() if soup.title else ""
            description = ""
            for meta in soup.find_all("meta"):
                if meta.get("name") == "description" or meta.get("property") == "og:description":
                    description = meta.get("content", "").strip()
                    break
            
            # Determine if it's a recipe
            is_recipe_result = is_recipe(url, title, description, clean_text)
            
            # Populate result
            result.update({
                'success': True,
                'is_recipe': is_recipe_result,
                'data': {
                    'clean_text': clean_text,
                    'markdown': markdown,
                    'title': title,
                    'description': description,
                    'proxy_used': proxy_used
                }
            })
            
            logger.info(f"Successfully processed URL: {url} (is_recipe={is_recipe_result})")
            
        except Exception as e:
            result['failure_reason'] = str(e)
            logger.error(f"Error processing URL {url}: {e}")
        
        return result

    def get_and_mark_urls_batch(self):
        """
        Get a batch of URLs and mark them as in progress synchronously
        
        Returns:
            list: List of dictionaries containing URL data
        """
        url_data = []
        
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Begin transaction
                cursor.execute("BEGIN")
                
                # Get batch of URLs to process
                cursor.execute(
                    """
                    SELECT id, url 
                    FROM recipe.recipe_urls 
                    WHERE status = 'crawl_pending' 
                    LIMIT %s
                    """,
                    (self.batch_size,)
                )
                urls = cursor.fetchall()
                
                if urls:
                    # Convert to list of dictionaries
                    url_data = [{'id': url['id'], 'url': url['url']} for url in urls]
                    url_ids = [url['id'] for url in url_data]
                    
                    # Mark URLs as in progress
                    cursor.execute(
                        """
                        UPDATE recipe.recipe_urls
                        SET status = 'crawl_in_progress' 
                        WHERE id = ANY(%s)
                        """,
                        (url_ids,)
                    )
                    
                    # Commit transaction
                    conn.commit()
                    logger.info(f"Fetched and marked {len(url_data)} URLs as in progress")
                else:
                    conn.commit()
                    logger.info("No URLs to process")
                    
            conn.close()
        except Exception as e:
            logger.error(f"Error getting and marking URLs batch: {e}")
            if 'conn' in locals() and conn:
                conn.rollback()
                conn.close()
        
        return url_data

    def update_processed_urls_batch(self, results):
        """
        Update processed URLs in the database in bulk
        
        Args:
            results (list): List of processing results
        
        Returns:
            dict: Statistics of updates
        """
        stats = {"successful": 0, "failed": 0}
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Begin transaction
                cursor.execute("BEGIN")
                
                # Process successful URLs
                successful_data = [
                    (
                        r['data']['clean_text'], r['data']['markdown'], r['data']['title'], 
                        r['data']['description'], datetime.utcnow(), r['data']['proxy_used'], 
                        'crawl_complete', r['is_recipe'], r['url_id']
                    )
                    for r in results if r['success']
                ]
                
                # Process failed URLs
                failed_data = [
                    ('crawl_failed', r.get('failure_reason', 'unknown_error'), 
                     datetime.utcnow(), r['url_id'])
                    for r in results if not r['success']
                ]
                
                # Update successful URLs
                if successful_data:
                    psycopg2.extras.execute_batch(
                        cursor,
                        """
                        UPDATE recipe.recipe_urls
                        SET parsed_text = %s, 
                            parsed_md = %s, 
                            title = %s, 
                            description = %s, 
                            last_crawled = %s, 
                            proxy_used = %s, 
                            status = %s, 
                            is_recipe = %s 
                        WHERE id = %s
                        """,
                        successful_data
                    )
                    stats["successful"] = len(successful_data)
                
                # Update failed URLs
                if failed_data:
                    psycopg2.extras.execute_batch(
                        cursor,
                        """
                        UPDATE recipe.recipe_urls 
                        SET status = %s, 
                            failure_reason = %s, 
                            last_attempt = %s 
                        WHERE id = %s
                        """,
                        failed_data
                    )
                    stats["failed"] = len(failed_data)
                
                # Commit transaction
                conn.commit()
                logger.info(f"Batch update completed: {stats['successful']} successful, {stats['failed']} failed")
                
            conn.close()
        except Exception as e:
            logger.error(f"Error updating processed URLs: {e}")
            if 'conn' in locals() and conn:
                conn.rollback()
                conn.close()
        
        return stats

    async def process_content(self):
        """
        Continuously process URLs
        """
        logger.info("Starting content processing loop")
        
        while True:
            # Get batch of URLs synchronously
            url_data = self.get_and_mark_urls_batch()
            
            if not url_data:
                logger.info("No URLs to process, waiting 5 seconds")
                await asyncio.sleep(5)
                continue
            
            batch_stats = {"total_processed": 0, "successful": 0, "failed": 0}
            
            try:
                logger.info(f"Processing batch of {len(url_data)} URLs")
                
                # Use semaphore to limit concurrency
                semaphore = asyncio.Semaphore(self.max_concurrency)
                
                async def process_with_semaphore(url):
                    async with semaphore:
                        return await self.process_url_async(url)
                
                # Process URLs concurrently
                results = await asyncio.gather(
                    *[process_with_semaphore(url) for url in url_data]
                )
                
                # Update processed URLs in bulk
                update_stats = self.update_processed_urls_batch(results)
                
                # Update batch statistics
                batch_stats.update({
                    "total_processed": len(results),
                    "successful": update_stats["successful"],
                    "failed": update_stats["failed"]
                })
                
                # Update total statistics
                for key in self.total_stats:
                    self.total_stats[key] += batch_stats[key]
                
                logger.info(f"Batch completed. Stats: {batch_stats}")
                logger.info(f"Running totals: {self.total_stats}")
            
            except Exception as e:
                logger.error(f"Error processing content batch: {e}")
            
            await asyncio.sleep(0.1)  # Prevent tight loop

async def main():
    parser = argparse.ArgumentParser(description="Process recipe URLs")
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size for processing URLs")
    parser.add_argument("--max-concurrency", type=int, default=16, help="Maximum concurrent URL processing")
    args = parser.parse_args()
    
    processor = ContentProcessor(
        batch_size=args.batch_size, 
        max_concurrency=args.max_concurrency
    )
    
    await processor.process_content()

if __name__ == "__main__":
    asyncio.run(main())