import logging
import warnings
import psycopg2
import psycopg2.extras
import urllib3
from datetime import datetime
from bs4 import BeautifulSoup
import html2text
from urllib.parse import urlparse
import argparse
import asyncio
import aiohttp
from config import setup_logging, get_db_connection
from utils import is_recipe, fetch_with_proxies

# Suppress insecure request warnings
warnings.simplefilter("ignore", psycopg2.errors.Warning)
warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)


def mark_url_failed(conn, url_id, reason):
    """Mark a URL as failed in the database"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE recipe_urls SET status = 'crawl_failed', failure_reason = %s, last_attempt = %s WHERE id = %s",
                (reason, datetime.utcnow(), url_id)
            )
            conn.commit()
            logger.warning(f"Failed to process URL ID {url_id}: {reason}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error marking URL as failed: {e}")


async def process_url_async(url_data):
    """Asynchronously process a URL to extract its content"""
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


def mark_urls_in_progress(conn, url_ids):
    """Mark multiple URLs as in progress in the database"""
    try:
        with conn.cursor() as cursor:
            psycopg2.extras.execute_values(
                cursor,
                "UPDATE recipe_urls SET status = 'crawl_in_progress' WHERE id = ANY(%s)",
                [(url_ids,)]
            )
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error marking URLs as in progress: {e}")
        return False


def update_processed_urls(conn, results):
    """Update multiple processed URLs in the database with their results"""
    stats = {"successful": 0, "failed": 0}
    
    try:
        # Process successful URLs
        successful_data = [
            (r['data']['clean_text'], r['data']['markdown'], r['data']['title'], 
             r['data']['description'], datetime.utcnow(), r['data']['proxy_used'], 
             'crawl_complete', r['is_recipe'], r['url_id'])
            for r in results if r['success']
        ]
        
        # Process failed URLs
        failed_data = [
            ('crawl_failed', r.get('failure_reason', 'unknown_error'), 
             datetime.utcnow(), r['url_id'])
            for r in results if not r['success']
        ]
        
        # Execute batch updates
        with conn.cursor() as cursor:
            if successful_data:
                psycopg2.extras.execute_values(
                    cursor,
                    """UPDATE recipe_urls AS r SET
                        parsed_text = d.parsed_text,
                        parsed_md = d.parsed_md,
                        title = d.title,
                        description = d.description,
                        last_crawled = d.last_crawled,
                        proxy_used = d.proxy_used,
                        status = d.status,
                        is_recipe = d.is_recipe
                    FROM (VALUES %s) AS d(parsed_text, parsed_md, title, description, 
                                          last_crawled, proxy_used, status, is_recipe, id)
                    WHERE r.id = d.id""",
                    successful_data,
                    template="(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                )
                stats["successful"] = len(successful_data)
            
            if failed_data:
                psycopg2.extras.execute_values(
                    cursor,
                    """UPDATE recipe_urls AS r SET
                        status = d.status,
                        failure_reason = d.failure_reason,
                        last_attempt = d.last_attempt
                    FROM (VALUES %s) AS d(status, failure_reason, last_attempt, id)
                    WHERE r.id = d.id""",
                    failed_data,
                    template="(%s, %s, %s, %s)"
                )
                stats["failed"] = len(failed_data)
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating processed URLs: {e}")
    
    return stats


async def process_content_async(batch_size=16):
    """Process URLs to extract content and save results asynchronously in a continuous loop"""
    total_stats = {"total_processed": 0, "successful": 0, "failed": 0}
    
    logger.info("Starting continuous URL processing loop")
    
    while True:
        conn = get_db_connection()
        batch_stats = {"total_processed": 0, "successful": 0, "failed": 0}
        
        try:
            # Get next batch of URLs to process
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    """SELECT id, url FROM recipe_urls 
                       WHERE status = 'crawl_pending'
                       LIMIT %s""",
                    (batch_size,)
                )
                urls = cursor.fetchall()
            
            if not urls:
                logger.info("No URLs to process, waiting 5 seconds before retrying")
                await asyncio.sleep(5)
                conn.close()
                continue
            
            logger.info(f"Processing batch of {len(urls)} URLs")
            
            # Mark URLs as in progress and process asynchronously
            url_ids = [url['id'] for url in urls]
            if mark_urls_in_progress(conn, url_ids):
                results = await asyncio.gather(*[process_url_async(url) for url in urls])
                update_stats = update_processed_urls(conn, results)
                
                batch_stats.update({
                    "total_processed": len(results),
                    "successful": update_stats["successful"],
                    "failed": update_stats["failed"]
                })
                
                # Update total stats
                for key in total_stats:
                    total_stats[key] += batch_stats[key]
                
                logger.info(f"Batch completed. Stats: {batch_stats}")
                logger.info(f"Running totals: {total_stats}")
            
        except Exception as e:
            logger.error(f"Error processing content batch: {e}")
        
        finally:
            conn.close()


async def main():
    parser = argparse.ArgumentParser(description="Process recipe URLs asynchronously")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size for processing URLs")
    args = parser.parse_args()
    
    logger.info(f"Starting continuous URL processing with batch size: {args.batch_size}")
    await process_content_async(batch_size=args.batch_size)


if __name__ == "__main__":
    asyncio.run(main())