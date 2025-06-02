from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config import DB_PATH
import datetime


# SQLAlchemy setup
Base = declarative_base()

class RecipeSite(Base):
    __tablename__ = 'recipe_sites'
    
    id = Column(Integer, primary_key=True)
    recipe_site_url = Column(String, unique=True, nullable=False)
    status = Column(String, default="new")
    # sitemap_count = Column(Integer, default=0)
    # total_url_count = Column(Integer, default=0)
    last_processed = Column(DateTime)
    manual_sitemaps = Column(String)  # Store as comma-separated values
    
    # Relationship
    sitemaps = relationship("Sitemap", back_populates="site")
    
class Sitemap(Base):
    __tablename__ = 'sitemaps'
    
    id = Column(Integer, primary_key=True)
    sitemap_url = Column(String, nullable=False)
    site_id = Column(Integer, ForeignKey('recipe_sites.id'))
    url_count = Column(Integer, default=0)
    
    # Relationship
    site = relationship("RecipeSite", back_populates="sitemaps")
    urls = relationship("RecipeUrl", back_populates="sitemap")

class RecipeUrl(Base):
    __tablename__ = 'recipe_urls'
    
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    sitemap_id = Column(Integer, ForeignKey('sitemaps.id'))
    last_modified = Column(String)
    last_extracted = Column(DateTime, default=datetime.utcnow)
    randnum = Column(Integer)
    
    # New fields for content
    is_recipe = Column(Boolean, nullable=True)
    parsed_text = Column(Text, nullable=True)
    parsed_md = Column(Text, nullable=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    recipe_json = Column(JSON, nullable=True)
    last_crawled = Column(DateTime, nullable=True)
    proxy_used = Column(String, nullable=True)
    status = Column(String, default="new")
    failure_reason = Column(String, nullable=True)
    last_attempt = Column(DateTime, nullable=True)
    
    # Relationship
    sitemap = relationship("Sitemap", back_populates="urls")

def get_db_session():
    """Create and return a new database session."""
    engine = create_engine(DB_PATH)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()