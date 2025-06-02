


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