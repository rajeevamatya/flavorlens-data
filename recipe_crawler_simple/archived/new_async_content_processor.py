import os
import logging
import asyncio
import argparse
import warnings
import asyncpg

from datetime import datetime
from bs4 import BeautifulSoup
import html2text

from config import setup_logging, create_async_db_pool
from utils import is_recipe, fetch_with_proxies

# Suppress warnings
warnings.simplefilter("ignore")

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)
logger.info("Logging setup complete.")

class AsyncContentProcessor:
    def __init__(self, batch_size=16, max_concurrency=16):
        """
        Initialize the async content processor
        
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

    async def mark_url_failed(self, conn, url_id, reason):
        """
        Mark a URL as failed in the database
        
        Args:
            conn (asyncpg.Connection): Database connection
            url_id (int): URL database ID
            reason (str): Reason for failure
        """
        try:
            await conn.execute(
                """
                UPDATE recipe_urls 
                SET status = 'crawl_failed', 
                    failure_reason = $1, 
                    last_attempt = $2 
                WHERE id = $3
                """,
                reason, 
                datetime.utcnow(), 
                url_id
            )
            logger.warning(f"Failed to process URL ID {url_id}: {reason}")
        except Exception as e:
            logger.error(f"Error marking URL as failed: {e}")

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
            soup = BeautifulSoup(content, "html.parser")
            
            # Remove unnecessary elements
            for tag in soup.find_all(["nav", "footer", "aside", "script", "style", "img"]):
                tag.decompose()
            
            # Extract text
            text = soup.get_text(separator="\n").strip()
            clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
            
            # Convert to markdown
            h2t = html2text.HTML2Text()
            h2t.ignore_links = h2t.ignore_images = True
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

    async def mark_urls_in_progress(self, conn, url_ids):
        """
        Mark multiple URLs as in progress
        
        Args:
            conn (asyncpg.Connection): Database connection
            url_ids (list): List of URL IDs to mark
        
        Returns:
            bool: Success status
        """
        try:
            await conn.execute(
                """
                UPDATE recipe_urls
                SET status = 'crawl_in_progress' 
                WHERE id = ANY($1)
                """,
                url_ids
            )
            return True
        except Exception as e:
            logger.error(f"Error marking URLs as in progress: {e}")
            return False

    async def update_processed_urls(self, conn, results):
        """
        Update processed URLs in the database
        
        Args:
            conn (asyncpg.Connection): Database connection
            results (list): List of processing results
        
        Returns:
            dict: Statistics of updates
        """
        stats = {"successful": 0, "failed": 0}
        
        try:
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
                await conn.executemany(
                    """
                    UPDATE recipe_urls
                    SET parsed_text = $1, 
                        parsed_md = $2, 
                        title = $3, 
                        description = $4, 
                        last_crawled = $5, 
                        proxy_used = $6, 
                        status = $7, 
                        is_recipe = $8 
                    WHERE id = $9
                    """,
                    successful_data
                )
                stats["successful"] = len(successful_data)
            
            # Update failed URLs
            if failed_data:
                await conn.executemany(
                    """
                    UPDATE recipe_urls 
                    SET status = $1, 
                        failure_reason = $2, 
                        last_attempt = $3 
                    WHERE id = $4
                    """,
                    failed_data
                )
                stats["failed"] = len(failed_data)
            
        except Exception as e:
            logger.error(f"Error updating processed URLs: {e}")
        
        return stats

    async def process_content_async(self):
        """
        Continuously process URLs asynchronously
        """
        logger.info("Starting continuous URL processing loop")
        
        # Create connection pool
        pool = await create_async_db_pool()
        
        while True:
            batch_stats = {
                "total_processed": 0,
                "successful": 0,
                "failed": 0
            }
            
            try:
                # Acquire a connection from the pool
                async with pool.acquire() as conn:
                    # Get next batch of URLs to process
                    urls = await conn.fetch(
                        """
                        SELECT id, url 
                        FROM recipe_urls 
                        WHERE status = 'crawl_pending' 
                        LIMIT $1
                        """,
                        self.batch_size
                    )
                    
                    if not urls:
                        logger.info("No URLs to process, waiting 5 seconds")
                        await asyncio.sleep(5)
                        continue
                    
                    logger.info(f"Processing batch of {len(urls)} URLs")
                    
                    # Convert urls to list of dictionaries
                    url_data = [{'id': url['id'], 'url': url['url']} for url in urls]
                    url_ids = [url['id'] for url in url_data]
                    
                    # Mark URLs as in progress
                    if await self.mark_urls_in_progress(conn, url_ids):
                        # Use semaphore to limit concurrency
                        semaphore = asyncio.Semaphore(self.max_concurrency)
                        
                        async def process_with_semaphore(url):
                            async with semaphore:
                                return await self.process_url_async(url)
                        
                        # Process URLs concurrently
                        results = await asyncio.gather(
                            *[process_with_semaphore(url) for url in url_data]
                        )
                        
                        # Update processed URLs
                        update_stats = await self.update_processed_urls(conn, results)
                        
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
    parser = argparse.ArgumentParser(description="Process recipe URLs asynchronously")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size for processing URLs")
    parser.add_argument("--max-concurrency", type=int, default=16, help="Maximum concurrent URL processing")
    args = parser.parse_args()
    
    processor = AsyncContentProcessor(
        batch_size=args.batch_size, 
        max_concurrency=args.max_concurrency
    )
    
    await processor.process_content_async()

if __name__ == "__main__":
    asyncio.run(main())