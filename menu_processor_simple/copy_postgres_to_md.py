#!/usr/bin/env python3
"""
Script to copy data from PostgreSQL to MotherDuck
Processes data in batches of 1000 rows
"""

import duckdb
import logging
from typing import List, Tuple, Any
import time

from config import get_db_connection, setup_logging, MOTHERDUCK_TOKEN, MD_DATABASE_URL

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


class DataCopier:
    def __init__(self):
        self.pg_conn = None
        self.duck_conn = None
        
    def connect_postgres(self):
        """Connect to PostgreSQL using config.py"""
        try:
            self.pg_conn = get_db_connection()
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
            
    def connect_motherduck(self):
        """Connect to MotherDuck using config.py"""
        try:
            # Use MD_DATABASE_URL if available, otherwise construct from token
            if MD_DATABASE_URL:
                self.duck_conn = duckdb.connect(MD_DATABASE_URL)
            else:
                self.duck_conn = duckdb.connect(f'md:?motherduck_token={MOTHERDUCK_TOKEN}')
            logger.info("Connected to MotherDuck")
        except Exception as e:
            logger.error(f"Failed to connect to MotherDuck: {e}")
            raise
    
    def copy_dishes(self):
        """Copy dishes table from PostgreSQL to MotherDuck"""
        logger.info("Starting dishes table copy...")
        
        # Clear MotherDuck table
        self.duck_conn.execute("DELETE FROM dishes")
        
        pg_cursor = self.pg_conn.cursor()
        
        # Get total count
        pg_cursor.execute("SELECT COUNT(*) FROM menu.dishes")
        total_rows = pg_cursor.fetchone()[0]
        logger.info(f"Total dishes to copy: {total_rows}")
        
        # Copy in batches
        offset = 0
        copied_rows = 0
        
        while offset < total_rows:
            pg_cursor.execute("""
                SELECT dish_id, dish_name, description, meal_time, general_category,
                       specific_category, cuisine, complexity, serving_temperature,
                       season, source, date_created, date_modified, star_rating,
                       num_ratings, num_reviews, date_published, date_updated
                FROM menu.dishes
                ORDER BY dish_id
                LIMIT %s OFFSET %s
            """, (BATCH_SIZE, offset))
            
            batch = pg_cursor.fetchall()
            if not batch:
                break
                
            # Prepare batch for MotherDuck
            motherduck_batch = []
            for row in batch:
                motherduck_row = (
                    str(row[0]),  # dish_id as string UUID
                    row[1],       # dish_name
                    row[2],       # description
                    None,         # dish_base_type (NULL)
                    row[3],       # meal_time
                    None,         # food_format (NULL)
                    row[4],       # general_category
                    row[5],       # specific_category
                    row[6],       # cuisine
                    None,         # country (NULL)
                    row[7],       # complexity
                    row[8],       # serving_temperature
                    row[9],       # season
                    row[10],      # source
                    row[17],      # date_updated (MotherDuck position 14)
                    row[16],      # date_published (MotherDuck position 15)
                    row[11],      # date_created (MotherDuck position 16)
                    row[12],      # date_modified (MotherDuck position 17)
                    float(row[13]) if row[13] else None,  # star_rating
                    row[14],      # num_ratings
                    row[15]       # num_reviews
                )
                motherduck_batch.append(motherduck_row)
            
            # Insert batch into MotherDuck (updated field order to match MotherDuck schema)
            self.duck_conn.executemany("""
                INSERT INTO dishes (
                    dish_id, dish_name, description, dish_base_type, meal_time,
                    food_format, general_category, specific_category, cuisine,
                    country, complexity, serving_temperature, season, source, 
                    date_updated, date_published, date_created, date_modified,
                    star_rating, num_ratings, num_reviews
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, motherduck_batch)
            
            copied_rows += len(batch)
            offset += BATCH_SIZE
            logger.info(f"Copied {copied_rows}/{total_rows} dishes")
            
        logger.info(f"Completed dishes copy: {copied_rows} rows")
    
    def copy_dish_ingredients(self):
        """Copy dish_ingredients table from PostgreSQL to MotherDuck"""
        logger.info("Starting dish_ingredients table copy...")
        
        # Clear MotherDuck table
        self.duck_conn.execute("DELETE FROM dish_ingredients")
        
        pg_cursor = self.pg_conn.cursor()
        
        # Get total count
        pg_cursor.execute("SELECT COUNT(*) FROM menu.dish_ingredients")
        total_rows = pg_cursor.fetchone()[0]
        logger.info(f"Total dish_ingredients to copy: {total_rows}")
        
        # Copy in batches
        offset = 0
        copied_rows = 0
        
        while offset < total_rows:
            pg_cursor.execute("""
                SELECT dish_id, ingredient_id, quantity, units, format, type,
                       ingredient_role, flavor_role, alternative_ingredients,
                       date_added, prep_method, ingredient, flavor_ingredient
                FROM menu.dish_ingredients
                ORDER BY dish_id, ingredient_id
                LIMIT %s OFFSET %s
            """, (BATCH_SIZE, offset))
            
            batch = pg_cursor.fetchall()
            if not batch:
                break
                
            # Prepare batch for MotherDuck
            motherduck_batch = []
            for row in batch:
                motherduck_row = (
                    str(row[0]),  # dish_id as string UUID
                    row[1],       # ingredient_id
                    row[12],      # flavor_ingredient -> name (index 12)
                    row[11],      # ingredient -> full_ingredient (index 11)
                    float(row[2]) if row[2] else None,  # quantity
                    row[3],       # units
                    row[4],       # format
                    row[5],       # type
                    row[6],       # ingredient_role
                    row[10],      # prep_method -> cooking_technique (index 10)
                    row[7],       # flavor_role
                    row[8],       # alternative_ingredients -> alternatives
                    None,         # flavor_notes (NULL)
                    row[9]        # date_added (index 9)
                )
                motherduck_batch.append(motherduck_row)
            
            # Insert batch into MotherDuck
            self.duck_conn.executemany("""
                INSERT INTO dish_ingredients (
                    dish_id, ingredient_id, name, full_ingredient, quantity,
                    units, format, type, ingredient_role, cooking_technique,
                    flavor_role, alternatives, flavor_notes, date_added
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, motherduck_batch)
            
            copied_rows += len(batch)
            offset += BATCH_SIZE
            logger.info(f"Copied {copied_rows}/{total_rows} dish_ingredients")
            
        logger.info(f"Completed dish_ingredients copy: {copied_rows} rows")
    
    def copy_dish_attributes(self):
        """Copy dish_attributes table from PostgreSQL to MotherDuck"""
        logger.info("Starting dish_attributes table copy...")
        
        # Clear MotherDuck table 
        self.duck_conn.execute("DELETE FROM dish_attributes")
        
        pg_cursor = self.pg_conn.cursor()
        
        # Get total count
        pg_cursor.execute("SELECT COUNT(*) FROM menu.dish_attributes")
        total_rows = pg_cursor.fetchone()[0]
        logger.info(f"Total dish_attributes to copy: {total_rows}")
        
        # Copy in batches
        offset = 0
        copied_rows = 0
        
        while offset < total_rows:
            pg_cursor.execute("""
                SELECT dish_id, flavor_attributes, texture_attributes, aroma_attributes,
                       diet_preferences, functional_health, occasions,
                       convenience_attributes, social_setting, emotional_attributes,
                       cooking_techniques
                FROM menu.dish_attributes
                ORDER BY dish_id
                LIMIT %s OFFSET %s
            """, (BATCH_SIZE, offset))
            
            batch = pg_cursor.fetchall()
            if not batch:
                break
                
            # Prepare batch for MotherDuck (cooking_techniques is last field)
            motherduck_batch = []
            for row in batch:
                motherduck_row = (
                    str(row[0]),  # dish_id as string UUID
                    row[1],       # flavor_attributes
                    row[2],       # texture_attributes
                    row[3],       # aroma_attributes
                    row[10],      # cooking_techniques (last field in PostgreSQL)
                    row[4],       # diet_preferences
                    row[5],       # functional_health
                    row[6],       # occasions
                    row[7],       # convenience_attributes
                    row[8],       # social_setting
                    row[9]        # emotional_attributes
                )
                motherduck_batch.append(motherduck_row)
            
            # Insert batch into MotherDuck (added cooking_techniques)
            self.duck_conn.executemany("""
                INSERT INTO dish_attributes (
                    dish_id, flavor_attributes, texture_attributes, aroma_attributes,
                    cooking_techniques, diet_preferences, functional_health, occasions,
                    convenience_attributes, social_setting, emotional_attributes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, motherduck_batch)
            
            copied_rows += len(batch)
            offset += BATCH_SIZE
            logger.info(f"Copied {copied_rows}/{total_rows} dish_attributes")
            
        logger.info(f"Completed dish_attributes copy: {copied_rows} rows")
    
    def run(self):
        """Run the complete data copy process"""
        try:
            # Connect to databases
            self.connect_postgres()
            self.connect_motherduck()
            
            start_time = time.time()
            
            # Copy tables in order (dishes first due to dependencies)
            self.copy_dishes()
            self.copy_dish_ingredients()
            self.copy_dish_attributes()
            
            elapsed_time = time.time() - start_time
            logger.info(f"Data copy completed successfully in {elapsed_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Data copy failed: {e}")
            raise
        finally:
            # Close connections
            if self.pg_conn:
                self.pg_conn.close()
                logger.info("PostgreSQL connection closed")
            if self.duck_conn:
                self.duck_conn.close()
                logger.info("MotherDuck connection closed")


if __name__ == "__main__":
    logger.info("Starting PostgreSQL to MotherDuck data copy...")
    logger.info("Using configuration from config.py")
    
    copier = DataCopier()
    copier.run()