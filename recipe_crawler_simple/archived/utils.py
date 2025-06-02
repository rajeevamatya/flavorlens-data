import requests
import logging
from urllib.parse import urlparse
from llm import extract_recipe_data, is_recipe_url, check_recipe_url_with_openai
import tldextract
from tenacity import retry, stop_after_attempt, wait_exponential, wait_fixed, retry_if_exception_type
import html2text
import re
import gzip
import chardet
from bs4 import BeautifulSoup
from config import DATACENTER_PROXY, PREMIUM_PROXY



@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
def fetch_url(url, proxy_url=DATACENTER_PROXY):
    """Fetch URL, defaulting to datacenter proxy, with fallback to premium, with 2 retries."""
    logging.debug(f"Fetching URL {url} with proxy: {proxy_url}")

    proxies_to_try = [proxy_url, PREMIUM_PROXY] if proxy_url == DATACENTER_PROXY else [proxy_url]

    for proxy in proxies_to_try:
        if not proxy:
            continue

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
        })
        session.proxies = {"http": proxy, "https": proxy}

        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            logging.info(f"Successfully fetched URL {url} using proxy {proxy}")
            return response, proxy if proxy_url != DATACENTER_PROXY else (
                "datacenter" if proxy == DATACENTER_PROXY else "premium"
            )

        except requests.exceptions.RequestException as e: # Catch specific request exceptions.
            logging.error(f"Error fetching URL {url} with proxy {proxy}: {e}")
            if proxy == PREMIUM_PROXY: # only reraise if we are at the last proxy
                raise e
        except Exception as e:
            logging.error(f"Unexpected error when fetching {url}: {e}")
            if proxy == PREMIUM_PROXY:
                raise e

    logging.warning(f"Failed to fetch URL {url} using all proxies")
    return None, None


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(requests.exceptions.RequestException))
def fetch_sitemap_with_fallback(sitemap_url):
    """
    Fetch sitemap with datacenter proxy, fallback to premium proxy, and handle compression.
    Args: sitemap_url: URL of the sitemap to fetch    
    Returns: str or None: The sitemap content if successful, None otherwise
    """
    proxies = [
        (DATACENTER_PROXY, "datacenter"),
        (PREMIUM_PROXY, "premium")
    ]

    for proxy_url, proxy_type in proxies:
        
        try:
            logging.info(f"Fetching {sitemap_url} with {proxy_type} proxy")
            response_tuple = fetch_url(sitemap_url, proxy_url)
            if response_tuple is None or response_tuple[0] is None:
                raise requests.exceptions.RequestException("Failed to fetch url via fetch_url function")
            response = response_tuple[0]
            content = response.content

            # Handle gzip compression if needed
            if sitemap_url.endswith('.gz') and content.startswith(b'\x1f\x8b'):
                try:
                    content = gzip.decompress(content)
                except Exception as e:
                    logging.error(f"Decompression error: {e}")
                    continue

            # Try to decode content
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                encoding = chardet.detect(content)['encoding'] or 'utf-8'
                return content.decode(encoding)
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed with {proxy_type} proxy: {e}")
            if proxy_type == "premium":
                raise e
            continue

        except Exception as e:
            logging.error(f"Unexpected error when fetching {sitemap_url}: {e}")
            if proxy_type == "premium":
              raise e
            continue


    logging.error(f"Failed to fetch sitemap {sitemap_url} with all proxies")
    return None


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=4, max=10))
def extract_page_content(url, openai_client):
    """Extract and process webpage content."""
    logging.info(f"Starting content extraction for URL: {url}")
    is_recipe = is_recipe_url(url, openai_client)  # Fixed: Using is_recipe_url instead of validate_recipe_url
    
    text, markdown, title, description, recipe_json = "", "", "", "", None
    proxy_used = None
    
    if is_recipe:
        response, proxy_used = fetch_url(url)
        if not response:
            logging.warning(f"No response received for URL: {url}")
            return text, markdown, title, description, recipe_json, proxy_used, is_recipe

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Clean up HTML
            for tag in soup.find_all(["nav", "footer", "aside", "script", "style", "img", "a"]):
                tag.decompose()

            # Extract text
            text = soup.get_text(separator="\n").strip()
            clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

            # Convert to markdown
            h2t = html2text.HTML2Text()
            h2t.ignore_links = True
            h2t.ignore_images = True
            markdown = h2t.handle(response.text)

            # Get title and description
            title = soup.title.string.strip() if soup.title else ""
            description = ""
            for meta in soup.find_all("meta"):
                if meta.get("name") == "description" or meta.get("property") == "og:description":
                    description = meta.get("content", "").strip()
                    break

            # Extract recipe data
            recipe_json = extract_recipe_data(clean_text, openai_client) if clean_text else None

            logging.info(f"Successfully extracted content for URL: {url}")
        except Exception as e:
            logging.error(f"Content extraction error for URL {url}: {e}")
    
    return text, markdown, title, description, recipe_json, proxy_used, is_recipe



def is_valid_url(url):
    """
    Validate if a URL is a valid recipe URL.
    Args: url: The URL to validate
    Returns: Optional[bool]: True if valid recipe URL, False if invalid, None if uncertain
    """
    try:
        parsed = urlparse(url)
        
        # Basic URL validation
        if not all([parsed.scheme, parsed.netloc]):
            return None
            
        if parsed.scheme not in ('http', 'https'):
            return None
            
        # Extract domain information
        ext = tldextract.extract(url)
        if not all([ext.domain, ext.suffix]):
            return None
            
        # Check for excluded patterns
        excluded_patterns = [
            r'\.(jpg|jpeg|png|gif|pdf|zip|doc|docx|xml|txt)$',
            r'/(sitemap|feed|rss|atom|api|admin|login|wp-content)/',
            r'/(tag|category|author|search)/',
        ]
        
        for pattern in excluded_patterns:
            if re.search(pattern, parsed.path.lower()):
                return False
                
        return True
        
    except Exception as e:
        logging.error(f"Error validating URL {url}: {str(e)}")
        return None


def is_recipe_url(url, client):
    """Checks if a URL is a recipe URL using path analysis and OpenAI."""
    logging.debug(f"Validating recipe URL: {url}")

    if 'recipe' in urlparse(url).path.lower():
        logging.info(f"URL contains 'recipe' in the path: {url}")
        return True

    is_recipe_url_openai = check_recipe_url_with_openai(url, client)
    logging.info(f"OpenAI API determined recipe status for {url}: {is_recipe_url_openai}")
    return is_recipe_url_openai





# def fetch_sitemap_with_fallback(sitemap_url, max_retries=2):
#     """
#     Fetch sitemap with datacenter proxy, fallback to premium proxy, and handle compression.
    
#     Args:
#         sitemap_url: URL of the sitemap to fetch
#         max_retries: Maximum number of retry attempts per proxy
    
#     Returns:
#         str or None: The sitemap content if successful, None otherwise
#     """
#     proxies = [
#         (DATACENTER_PROXY, "datacenter"),
#         (PREMIUM_PROXY, "premium")
#     ]

#     for proxy_url, proxy_type in proxies:
#         session = create_proxy_session(proxy_url)
        
#         for attempt in range(max_retries):
#             try:
#                 logging.info(f"Fetching {sitemap_url} with {proxy_type} proxy (attempt {attempt + 1})")
#                 response = session.get(sitemap_url, timeout=30, verify=False)
#                 response.raise_for_status()
#                 content = response.content

#                 # Handle gzip compression if needed
#                 if sitemap_url.endswith('.gz') and content.startswith(b'\x1f\x8b'):
#                     try:
#                         content = gzip.decompress(content)
#                     except Exception as e:
#                         logging.error(f"Decompression error: {e}")
#                         continue

#                 # Try to decode content
#                 try:
#                     return content.decode('utf-8')
#                 except UnicodeDecodeError:
#                     encoding = chardet.detect(content)['encoding'] or 'utf-8'
#                     return content.decode(encoding)

#             except requests.exceptions.RequestException as e:
#                 logging.error(f"Request failed with {proxy_type} proxy (attempt {attempt + 1}): {e}")
#                 if attempt < max_retries - 1:
#                     time.sleep(2 * (attempt + 1))  # Simple backoff
#                 continue
            
#             finally:
#                 session.close()

#     logging.error(f"Failed to fetch sitemap {sitemap_url} with all proxies")
#     return None