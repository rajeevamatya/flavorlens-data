import requests
import aiohttp
import asyncio
import logging
import gzip
import chardet
import re
from urllib.parse import urlparse
import tldextract
from tenacity import retry, stop_after_attempt, wait_fixed
from config import DATACENTER_PROXY, PREMIUM_PROXY

logger = logging.getLogger(__name__)


def is_recipe(url, title, description, content):
    """Determines if content is a recipe based on simple but effective rules."""
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


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
async def fetch_with_proxies(url):
    """Fetch URL with datacenter proxy fallback to premium proxy"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
    }
    
    proxies = [
        (DATACENTER_PROXY, "datacenter"),
        (PREMIUM_PROXY, "premium")
    ]
    
    async with aiohttp.ClientSession(headers=headers) as session:
        for proxy_url, proxy_type in proxies:
            if not proxy_url:
                continue
                
            try:
                async with session.get(
                    url,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    ssl=False
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.info(f"Fetched {url} using {proxy_type} proxy")
                        return content, proxy_type
                    else:
                        raise Exception(f"HTTP {response.status}")
                        
            except Exception as e:
                logger.warning(f"Failed {url} with {proxy_type} proxy: {e}")
                continue
    
    logger.error(f"All proxies failed for {url}")
    return None, None


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
def fetch_sitemap_with_fallback(sitemap_url):
    """Fetch sitemap with proxy fallback and handle compression"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
    }
    
    proxies = [
        (DATACENTER_PROXY, "datacenter"),
        (PREMIUM_PROXY, "premium")
    ]
    
    for proxy_url, proxy_type in proxies:
        if not proxy_url:
            continue
            
        try:
            response = requests.get(
                sitemap_url,
                proxies={"http": proxy_url, "https": proxy_url},
                headers=headers,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            
            content = response.content
            
            # Handle gzip compression
            if sitemap_url.endswith('.gz') or content.startswith(b'\x1f\x8b'):
                try:
                    content = gzip.decompress(content)
                except Exception as e:
                    logger.error(f"Decompression failed for {sitemap_url}: {e}")
                    continue
            
            # Decode content
            try:
                decoded_content = content.decode('utf-8')
            except UnicodeDecodeError:
                encoding = chardet.detect(content).get('encoding', 'utf-8')
                decoded_content = content.decode(encoding, errors='ignore')
            
            logger.info(f"Fetched sitemap {sitemap_url} using {proxy_type} proxy")
            return decoded_content
            
        except Exception as e:
            logger.warning(f"Failed sitemap {sitemap_url} with {proxy_type} proxy: {e}")
            continue
    
    logger.error(f"All proxies failed for sitemap {sitemap_url}")
    return None


def is_valid_url(url):
    """Check if URL is valid and not an excluded file type or path"""
    if not url:
        return False
        
    try:
        parsed = urlparse(url)
        
        # Basic validation
        if not (parsed.scheme and parsed.netloc and parsed.scheme in ('http', 'https')):
            return False
        
        # Domain validation
        ext = tldextract.extract(url)
        if not (ext.domain and ext.suffix):
            return False
        
        # Exclude unwanted patterns
        excluded = [
            r'\.(jpg|jpeg|png|gif|pdf|zip|doc|docx|xml|txt)$',
            r'/(sitemap|feed|rss|atom|api|admin|login|wp-content|tag|category|author|search)/'
        ]
        
        
        path = parsed.path.lower()
        return not any(re.search(pattern, path) for pattern in excluded)
        
    except Exception:
        return False
    

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