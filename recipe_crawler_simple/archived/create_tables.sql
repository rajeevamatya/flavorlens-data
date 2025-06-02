-- Table for storing recipe sites
CREATE TABLE recipe_sites (
    id SERIAL PRIMARY KEY,
    recipe_site_url TEXT NOT NULL,
    manual_sitemaps TEXT,
    status TEXT DEFAULT 'url_extraction_pending',
    last_processed TIMESTAMP,
    CONSTRAINT unique_site_url UNIQUE (recipe_site_url)
);

-- Table for storing recipe URLs extracted from sitemaps
CREATE TABLE recipe_urls (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    site_id INTEGER REFERENCES recipe_sites(id),
    sitemap_url TEXT,
    last_modified TIMESTAMP,
    last_extracted TIMESTAMP,
    last_crawled TIMESTAMP,
    last_attempt TIMESTAMP,
    status TEXT DEFAULT 'crawl_pending',
    failure_reason TEXT,
    parsed_text TEXT,
    parsed_md TEXT,
    title TEXT,
    description TEXT,
    proxy_used TEXT,
    is_recipe BOOLEAN,
    randnum INTEGER,
    CONSTRAINT unique_url UNIQUE (url)
);