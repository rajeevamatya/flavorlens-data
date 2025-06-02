def test_site_url(site_url, manual_sitemaps=None, limit=20):
    """
    Test function to crawl a single site URL without any database operations
    
    Args:
        site_url (str): The URL of the recipe site to test
        manual_sitemaps (str, optional): Comma-separated list of manual sitemap URLs
        limit (int, optional): Maximum number of URLs to print per sitemap
        
    Returns:
        dict: Statistics and sample of URLs found
    """
    logger.info(f"Testing sitemap crawling for: {site_url}")
    
    # Get sitemaps and URLs
    sitemap_url_dict = get_sitemaps_and_urls(site_url, manual_sitemaps)
    
    # Prepare statistics and samples
    results = {
        "stats": {
            "sitemaps_found": len(sitemap_url_dict),
            "total_urls_found": sum(len(urls) for urls in sitemap_url_dict.values())
        },
        "sitemaps": {}
    }
    
    # Process each sitemap for stats and samples
    for sitemap_url, urls_data in sitemap_url_dict.items():
        # Create a limited sample of URLs
        url_sample = urls_data[:limit] if len(urls_data) > limit else urls_data
        
        results["sitemaps"][sitemap_url] = {
            "urls_found": len(urls_data),
            "url_samples": [url_data["url"] for url_data in url_sample]
        }
    
    # Print results
    logger.info(f"Test results for {site_url}:")
    logger.info(f"Found {results['stats']['sitemaps_found']} sitemaps with {results['stats']['total_urls_found']} total URLs")
    
    for sitemap_url, data in results["sitemaps"].items():
        logger.info(f"\nSitemap: {sitemap_url}")
        logger.info(f"URLs found: {data['urls_found']}")
        
        if data['url_samples']:
            logger.info(f"Sample URLs (up to {limit}):")
            for url in data['url_samples']:
                logger.info(f"  - {url}")
    
    return results




async def test_url_async(url):
    """Test function to process a single URL without saving to the database"""
    print(f"Testing URL: {url}")
    
    try:
        # Fetch and parse content
        print("\nFetching content...")
        content, proxy_used = await fetch_with_proxies(url)
        
        if not content:
            print("Error: Could not fetch URL (no response after all retries)")
            return
        
        print(f"Proxy used: {proxy_used}")
        soup = BeautifulSoup(content, "html.parser")
        
        # Extract metadata
        title = soup.title.string.strip() if soup.title else ""
        print(f"\nTitle: {title}")
        
        description = ""
        for meta in soup.find_all("meta"):
            if meta.get("name") == "description" or meta.get("property") == "og:description":
                description = meta.get("content", "").strip()
                break
        print(f"Description: {description}")
        
        # Clean HTML and extract text
        for tag in soup.find_all(["nav", "footer", "aside", "script", "style", "img"]):
            tag.decompose()
        
        text = soup.get_text(separator="\n").strip()
        clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        
        # Convert to markdown
        h2t = html2text.HTML2Text()
        h2t.ignore_links = h2t.ignore_images = True
        markdown = h2t.handle(content)
        
        # Check if it's a recipe
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