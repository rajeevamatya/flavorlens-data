import logging
import json
import asyncio
from datetime import datetime
from openai import AsyncAzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config import AZURE_API_ENDPOINT, AZURE_API_KEY, AZURE_API_VERSION, setup_logging, get_db_connection
from prompts import RESPONSE_FORMAT_RECIPE_EXTRACTION, SYSTEM_PROMPT_RECIPE_EXTRACTION

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)
logger.info("Logging setup complete.")

# Set hard batch limit
BATCH_LIMIT = 16

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=4, max=10))
async def extract_recipe_data(url_id, text, client):
    """Extract recipe data using AsyncAzureOpenAI."""
    try:
        logging.info(f"Extracting recipe data for URL ID {url_id} using OpenAI")
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_RECIPE_EXTRACTION},
                {"role": "user", "content": text}
            ],
            response_format=RESPONSE_FORMAT_RECIPE_EXTRACTION
        )
        response = completion.choices[0].message.content
        logging.debug(f"OpenAI extraction response received for URL ID {url_id}")
        return url_id, json.loads(response) if response else {}
    except Exception as e:
        logging.error(f"OpenAI extraction error for URL ID {url_id}: {e}")
        return url_id, {}


def get_urls_to_process(conn, limit=BATCH_LIMIT):
    """Get next URLs to process from the database using psycopg2."""
    logging.debug(f"Fetching next {limit} URLs to process from the database")
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, url, parsed_text 
                FROM recipe_urls 
                WHERE is_recipe IS TRUE
                AND last_crawled IS NOT NULL
                AND parsed_text IS NOT NULL
                AND recipe_json IS NULL
                AND status NOT IN ('json_in_progress', 'json_failed')
                LIMIT %s
                """,
                (limit,)
            )
            urls = cursor.fetchall()
            
            if not urls:
                logging.info("No recipe URLs found to process")
                return []
            
            # Mark all as in progress in a single transaction
            url_ids = [url[0] for url in urls]
            cursor.execute(
                """
                UPDATE recipe_urls 
                SET status = 'json_in_progress' 
                WHERE id IN %s
                """,
                (tuple(url_ids),)
            )
            conn.commit()
            
            # Return list of dictionaries for consistent interface
            return [{"id": url[0], "url": url[1], "parsed_text": url[2]} for url in urls]
            
    except Exception as e:
        conn.rollback()
        logging.error(f"Error getting URLs to process: {e}")
        return []


def update_url_with_recipe_json(conn, url_id, recipe_json):
    """Update a URL with extracted recipe JSON data using psycopg2."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE recipe_urls 
                SET recipe_json = %s, 
                    status = 'json_complete' 
                WHERE id = %s
                """,
                (json.dumps(recipe_json), url_id)
            )
            conn.commit()
            logging.info(f"Successfully updated URL ID {url_id} with recipe JSON")
    except Exception as e:
        conn.rollback()
        logging.error(f"Error updating URL ID {url_id} with recipe JSON: {e}")
        handle_extraction_failure(conn, url_id, str(e))


def handle_extraction_failure(conn, url_id, reason="unknown_error"):
    """Handle extraction failures using psycopg2."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE recipe_urls 
                SET status = 'json_failed', 
                    failure_reason = %s, 
                    last_attempt = %s 
                WHERE id = %s
                """,
                (reason, datetime.utcnow(), url_id)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error(f"Error handling extraction failure for URL ID {url_id}: {e}")


async def process_url_batch(conn, openai_client, urls):
    """Process a batch of URLs to extract recipe JSON asynchronously."""
    if not urls:
        logging.info("No URLs to process")
        return 0
    
    logging.info(f"Processing batch of {len(urls)} URLs")
    
    # Create a list of extraction tasks
    tasks = []
    
    for url_obj in urls:
        if not url_obj["parsed_text"]:
            logging.warning(f"No text content found for URL ID {url_obj['id']}: {url_obj['url']}")
            handle_extraction_failure(conn, url_obj["id"], "no_text_content")
            continue
            
        tasks.append(extract_recipe_data(url_obj["id"], url_obj["parsed_text"], openai_client))
    
    # Run extraction tasks concurrently and gather results
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    success_count = 0
    for result in results:
        if isinstance(result, Exception):
            logging.error(f"Extraction task exception: {result}")
            continue
            
        url_id, recipe_json = result
        if recipe_json:
            update_url_with_recipe_json(conn, url_id, recipe_json)
            success_count += 1
        else:
            handle_extraction_failure(conn, url_id, "extraction_failed")
    
    return len(urls)


async def main():
    """Main execution function with hard batch limit of 16."""
    logging.info(f"Starting async recipe JSON extraction with hard batch limit of {BATCH_LIMIT}")
    
    try:
        openai_client = AsyncAzureOpenAI(
            api_key=AZURE_API_KEY, 
            api_version=AZURE_API_VERSION, 
            azure_endpoint=AZURE_API_ENDPOINT
        )
        
        conn = get_db_connection()
        try:
            # Get batch of URLs to process
            urls = get_urls_to_process(conn, BATCH_LIMIT)
            if not urls:
                logging.info("No URLs to process")
                return
                
            # Process URLs asynchronously
            processed_count = await process_url_batch(conn, openai_client, urls)
            logging.info(f"Processed {processed_count}/{BATCH_LIMIT} URLs")
                
        finally:
            conn.close()

    except Exception as e:
        logging.error(f"Main loop error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Script failed: {e}")
        exit(1)