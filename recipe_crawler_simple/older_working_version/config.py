from dotenv import load_dotenv
import os
import logging
import psycopg2
import asyncpg
from contextlib import contextmanager


# Load environment variables from .env file
load_dotenv()

def setup_logging():
    """Sets up logging configuration for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )

# Proxy Settings
DATACENTER_PROXY = os.getenv("DATACENTER_PROXY")
PREMIUM_PROXY = os.getenv("PREMIUM_PROXY")

# API Keys and Endpoints
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION")
AZURE_API_ENDPOINT = os.getenv("AZURE_API_ENDPOINT")

# Database URL (Make sure it's PostgreSQL if using psycopg2)
DB_URL = os.getenv("DB_URL")

def get_db_connection():
    """Create a synchronous database connection using psycopg2"""
    # Replace with your actual connection details from config
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", 5432),
    )
    return conn