import logging
from datetime import datetime
from openai import AzureOpenAI, OpenAIError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import AZURE_API_ENDPOINT, AZURE_API_KEY, AZURE_API_VERSION, setup_logging, DB_PATH
from llm import is_recipe_url, extract_page_content
from db import RecipeUrl, get_db_session

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)
logger.info("Logging setup complete.")

def get_url_to_process(session, client):
    """Get next URL to process from the database."""
    logging.debug("Fetching next URL to process from the database")

    url = session.query(RecipeUrl).filter(
        RecipeUrl.randnum == 7,
        RecipeUrl.is_recipe.is_(None),
        RecipeUrl.last_crawled.is_(None),
        RecipeUrl.status.notin_(["crawl_in_progress", "crawl_failed"])
    ).first()

    if url and is_recipe_url(url.url, client): #url.url
        url.status = "crawl_in_progress"
        session.commit()
        return url

    if url and not is_recipe_url(url.url, client):
        url.is_recipe = False
        session.commit()
        return None

    return None


def process_url(session, openai_client, url_obj):
    """Process a single URL."""
    if not url_obj:
        logging.info("No URL to process")
        return

    url = url_obj.url
    logging.info(f"Processing URL: {url}")

    try:
        text, markdown, title, description, recipe_json, proxy_used, is_recipe = extract_page_content(url, openai_client)

        if not text and not recipe_json:
            logging.warning(f"No content extracted for URL: {url}")
            url_obj.status = "crawl_failed"
            url_obj.failure_reason = "no_content_extracted"
            url_obj.last_attempt = datetime.utcnow()
            session.commit()
            return

        url_obj.is_recipe = is_recipe
        url_obj.parsed_text = text
        url_obj.parsed_md = markdown
        url_obj.title = title
        url_obj.description = description
        url_obj.recipe_json = recipe_json
        url_obj.last_crawled = datetime.utcnow()
        url_obj.proxy_used = proxy_used
        url_obj.status = "crawl_complete"
        session.commit()
        
        logging.info(f"Successfully processed URL: {url}")

    except Exception as e:
        logging.error(f"Error processing URL {url}: {e}")
        url_obj.status = "crawl_failed"
        url_obj.failure_reason = str(e)
        url_obj.last_attempt = datetime.utcnow()
        session.commit()

def main():
    """Main execution function."""
    logging.info("Starting main execution loop")
    
    try:
        openai_client = AzureOpenAI(
            api_key=AZURE_API_KEY, 
            api_version=AZURE_API_VERSION, 
            azure_endpoint=AZURE_API_ENDPOINT
        )
        
        session = get_db_session() # Create a session object.
        try:
            while True:
                url_obj = get_url_to_process(session, openai_client)  # Fixed: passing openai_client
                if not url_obj:
                    logging.info("No more URLs to process")
                    break
                    
                process_url(session, openai_client, url_obj)
        finally:
            session.close() # Close session in finally block.

    except Exception as e:
        logging.error(f"Main loop error: {e}")

if __name__ == "__main__":
    main()