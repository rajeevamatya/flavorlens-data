from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env file
load_dotenv()

def setup_logging(log_filename="menu_analysis.log"):
    """Sets up logging configuration for the application."""
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )

DB_PATH = "sqlite:///recipes.db"


# # MongoDB Settings
# MONGO_URI = os.getenv("MONGO_URI")
# DB_NAME = os.getenv("DB_NAME")
# SITE_COLLECTION_NAME = os.getenv("SITE_COLLECTION_NAME")
# RECIPE_COLLECTION_NAME = os.getenv("RECIPE_COLLECTION_NAME")

# Proxy Settings
DATACENTER_PROXY = os.getenv("DATACENTER_PROXY")
PREMIUM_PROXY = os.getenv("PREMIUM_PROXY")

# API Keys and Endpoints
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION")
AZURE_API_ENDPOINT = os.getenv("AZURE_API_ENDPOINT")
