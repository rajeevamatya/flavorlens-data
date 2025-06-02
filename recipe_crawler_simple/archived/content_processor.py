import logging
import warnings
import psycopg2
import psycopg2.extras
from datetime import datetime
from bs4 import BeautifulSoup
import html2text
from urllib.parse import urlparse
import argparse
import requests

from config import setup_logging, get_db_connection
from utils import fetch_url

# Suppress insecure request warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter("ignore", InsecureRequestWarning)

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# @retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
# def fetch_url(url, proxy_url=DATACENTER_PROXY):
#     """Fetch URL, defaulting to datacenter proxy, with fallback to premium, with 2 retries."""
#     logging.debug(f"Fetching URL {url} with proxy: {proxy_url}")

#     proxies_to_try = [proxy_url, PREMIUM_PROXY] if proxy_url == DATACENTER_PROXY else [proxy_url]

#     for proxy in proxies_to_try:
#         if not proxy:
#             continue

#         session = requests.Session()
#         session.headers.update({
#             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
#         })
#         session.proxies = {"http": proxy, "https": proxy}

#         try:
#             response = session.get(url, timeout=10, verify=False)
#             response.raise_for_status()
#             logging.info(f"Successfully fetched URL {url} using proxy {proxy}")
#             return response, proxy if proxy_url != DATACENTER_PROXY else (
#                 "datacenter" if proxy == DATACENTER_PROXY else "premium"
#             )

#         except requests.exceptions.RequestException as e: # Catch specific request exceptions.
#             logging.error(f"Error fetching URL {url} with proxy {proxy}: {e}")
#             if proxy == PREMIUM_PROXY: # only reraise if we are at the last proxy
#                 raise e
#         except Exception as e:
#             logging.error(f"Unexpected error when fetching {url}: {e}")
#             if proxy == PREMIUM_PROXY:
#                 raise e

#     logging.warning(f"Failed to fetch URL {url} using all proxies")
#     return None, None

def is_recipe(url, title, description, content):
    """
    Determines if content is a recipe based on simple but effective rules.
    
    Args:
        url (str): The URL of the page
        title (str): The title of the page
        description (str): The meta description of the page
        content (str): The main text content of the page
        
    Returns:
        bool: True if it's likely a recipe, False otherwise
    """
    # Convert all inputs to lowercase for case-insensitive matching
    url = url.lower() if url else ""
    title = title.lower() if title else ""
    description = description.lower() if description else ""
    content = content.lower() if content else ""
    
    # Rule 1: Check if 'recipe' is in the URL path
    if 'recipe' in urlparse(url).path.lower():
        return True
    
    # Rule 2: Check if 'recipe' is in the title or description
    if 'recipe' in title or 'recipe' in description:
        return True
    
    # Rule 3: Check if both ingredient-related terms AND instruction-related terms appear in content
    has_ingredients = 'ingredient' in content or 'ingredients' in content
    has_instructions = any(term in content for term in ['instruction', 'instructions', 'direction', 'directions', 'steps', 'step'])
    
    if has_ingredients and has_instructions:
        return True
    
    # If none of the rules matched, it's probably not a recipe
    return False


def mark_url_failed(conn, url_id, reason):
    """
    Mark a URL as failed in the database
    
    Args:
        conn: Database connection
        url_id (int): ID of the URL to mark as failed
        reason (str): Reason for failure
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE recipe_urls 
                SET status = 'crawl_failed', 
                    failure_reason = %s, 
                    last_attempt = %s 
                WHERE id = %s
                """,
                (reason, datetime.utcnow(), url_id)
            )
            conn.commit()
            logger.warning(f"Failed to process URL ID {url_id}: {reason}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error marking URL as failed: {e}")


def process_url(conn, url_data):
    """
    Process a single URL to extract and save its content
    
    Args:
        conn: Database connection
        url_data (dict): Dictionary containing URL data
    
    Returns:
        bool: True if processed successfully, False otherwise
    """
    url_id = url_data['id']
    url = url_data['url']
    logger.info(f"Processing URL: {url}")
    
    # Mark as in progress
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE recipe_urls SET status = 'crawl_in_progress' WHERE id = %s",
                (url_id,)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating URL status: {e}")
        return False
    
    try:
        # Fetch content
        response, proxy_used = fetch_url(url)
        
        if not response:
            mark_url_failed(conn, url_id, "no_response")
            return False
        
        # Parse content
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Clean up HTML
        for tag in soup.find_all(["nav", "footer", "aside", "script", "style", "img"]):
            tag.decompose()
        
        # Extract text
        text = soup.get_text(separator="\n").strip()
        clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        
        # Convert to markdown
        h2t = html2text.HTML2Text()
        h2t.ignore_links = True
        h2t.ignore_images = True
        markdown = h2t.handle(response.text)
        
        # Extract metadata
        title = soup.title.string.strip() if soup.title else ""
        description = ""
        for meta in soup.find_all("meta"):
            if meta.get("name") == "description" or meta.get("property") == "og:description":
                description = meta.get("content", "").strip()
                break
        
        # Determine if it's a recipe using our simplified logic
        is_recipe_result = is_recipe(url, title, description, clean_text)
        
        # Update database
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE recipe_urls 
                SET parsed_text = %s, 
                    parsed_md = %s, 
                    title = %s, 
                    description = %s, 
                    last_crawled = %s, 
                    proxy_used = %s, 
                    status = 'crawl_complete', 
                    is_recipe = %s 
                WHERE id = %s
                """,
                (
                    clean_text, 
                    markdown, 
                    title, 
                    description, 
                    datetime.utcnow(), 
                    str(proxy_used), 
                    is_recipe_result, 
                    url_id
                )
            )
            conn.commit()
        
        logger.info(f"Successfully processed URL: {url} (is_recipe={is_recipe_result})")
        return True
        
    except Exception as e:
        mark_url_failed(conn, url_id, str(e))
        return False


def process_content(batch_size=50):
    """
    Process URLs to extract content and save results
    
    Args:
        batch_size (int, optional): Number of URLs to process in each batch
        
    Returns:
        dict: Statistics about the operation
    """
    conn = get_db_connection()
    
    stats = {
        "total_processed": 0,
        "successful": 0,
        "failed": 0
    }
    
    try:
        # Get next batch of URLs to process
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, url 
                FROM recipe_urls 
                WHERE status NOT IN ('crawl_complete', 'crawl_in_progress', 'crawl_failed')
                LIMIT %s
                """,
                (batch_size,)
            )
            urls = cursor.fetchall()
        
        logger.info(f"Processing batch of {len(urls)} URLs")
        
        for url_data in urls:
            success = process_url(conn, url_data)
            stats["total_processed"] += 1
            
            if success:
                stats["successful"] += 1
            else:
                stats["failed"] += 1
        
    except Exception as e:
        logger.error(f"Error processing content batch: {e}")
        conn.rollback()
    
    finally:
        conn.close()
    
    logger.info(f"Content processing completed. Stats: {stats}")
    return stats


def test_url(url):
    """
    Test function to process a single URL and print out all relevant information
    without saving to the database
    
    Args:
        url (str): URL to process
    """
    print(f"Testing URL: {url}")
    
    try:
        # Fetch content
        print(f"\nFetching content...")
        response, proxy_used = fetch_url(url)
        
        if not response:
            print(f"Error: Could not fetch URL (no response)")
            return
        
        print(f"Response status: {response.status_code}")
        print(f"Proxy used: {proxy_used}")
        
        # Parse content
        print(f"\nParsing HTML...")
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract metadata
        title = soup.title.string.strip() if soup.title else ""
        print(f"\nTitle: {title}")
        
        description = ""
        for meta in soup.find_all("meta"):
            if meta.get("name") == "description" or meta.get("property") == "og:description":
                description = meta.get("content", "").strip()
                break
        print(f"Description: {description}")
        
        # Clean up HTML for text extraction
        print(f"\nCleaning HTML...")
        for tag in soup.find_all(["nav", "footer", "aside", "script", "style", "img"]):
            tag.decompose()
        
        # Extract text
        text = soup.get_text(separator="\n").strip()
        clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        
        # Convert to markdown
        h2t = html2text.HTML2Text()
        h2t.ignore_links = True
        h2t.ignore_images = True
        markdown = h2t.handle(response.text)
        
        # Determine if it's a recipe
        is_recipe_result = is_recipe(url, title, description, clean_text)
        print(f"\nIs Recipe: {is_recipe_result}")
        
        # Print recipe identification factors
        print("\nRecipe identification factors:")
        print(f"- 'recipe' in URL path: {'recipe' in urlparse(url).path.lower()}")
        print(f"- 'recipe' in title: {'recipe' in title.lower() if title else False}")
        print(f"- 'recipe' in description: {'recipe' in description.lower() if description else False}")
        
        has_ingredients = 'ingredient' in clean_text.lower() or 'ingredients' in clean_text.lower()
        has_instructions = any(term in clean_text.lower() for term in ['instruction', 'instructions', 'direction', 'directions', 'steps', 'step'])
        print(f"- Has ingredients mention: {has_ingredients}")
        print(f"- Has instructions mention: {has_instructions}")
        
        # Print content snippets
        print("\nContent Preview (first 500 chars):")
        print("-----------------------------------")
        print(clean_text[:500] + "..." if len(clean_text) > 500 else clean_text)
        print("-----------------------------------")
        
        print("\nMarkdown Preview (first 500 chars):")
        print("-----------------------------------")
        print(markdown[:500] + "..." if len(markdown) > 500 else markdown)
        print("-----------------------------------")
        
        print("\nTest completed successfully.")
        
    except Exception as e:
        print(f"Error processing URL: {e}")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process recipe URLs")
    parser.add_argument("--test", type=str, help="Test a specific URL and print results")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing URLs")
    args = parser.parse_args()
    
    if args.test:
        # Run test mode for a single URL
        test_url(args.test)
    else:
        # Run normal processing
        logger.info("Starting content processing for URLs")
        stats = process_content(batch_size=args.batch_size)
        logger.info(f"Content processing completed. Processed: {stats['total_processed']}, Successful: {stats['successful']}, Failed: {stats['failed']}")