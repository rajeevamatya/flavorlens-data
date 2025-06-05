# Updated Recipe Extractor (main.py)
import logging
import asyncio
from openai import AsyncAzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config import AZURE_API_ENDPOINT, AZURE_API_KEY, AZURE_API_VERSION, setup_logging, get_db_connection
from recipe_prompts import SYSTEM_PROMPT_RECIPE_EXTRACTION, DishModel

setup_logging()
logger = logging.getLogger(__name__)


class RecipeExtractor:
    def __init__(self, batch_size=32, max_concurrency=8):
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.client = AsyncAzureOpenAI(
            api_key=AZURE_API_KEY, 
            api_version="2024-12-01-preview", 
            azure_endpoint="https://locmatic-menu-recipe.openai.azure.com/",
            timeout=60.0,
        )

    def get_pending_recipes(self):
        """Get recipes that need extraction"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """SELECT id, parsed_text, title, description
                       FROM recipe.recipe_urls 
                       WHERE is_recipe IS TRUE AND crawl_status = 'complete' AND parsed_text IS NOT NULL
                       AND llm_status = 'pending'
                       ORDER BY last_crawled DESC LIMIT %s""",
                    (self.batch_size,)
                )
                return cursor.fetchall()

    def update_llm_status(self, url_id, status, failure_reason=None):
        """Update LLM processing status"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE recipe.recipe_urls 
                    SET llm_status = %s, llm_failure_reason = %s
                    WHERE id = %s
                """, (status, failure_reason, url_id))
                conn.commit()

    def truncate_content(self, content, max_chars=8000):
        """Truncate content to avoid token limits"""
        if len(content) <= max_chars:
            return content
        
        # Try to find a good breaking point
        truncated = content[:max_chars]
        last_newline = truncated.rfind('\n')
        if last_newline > max_chars * 0.8:  # If we can break at a reasonable point
            return truncated[:last_newline] + "\n[Content truncated for processing]"
        return truncated + "\n[Content truncated for processing]"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def extract_recipe(self, recipe_data):
        """Extract structured recipe data using OpenAI"""
        url_id, text, title, description = recipe_data
        
        async with self.semaphore:
            try:
                # Truncate content to avoid token limits
                content = f"Title: {title or ''}\nDescription: {description or ''}\nContent:\n{text}"
                content = self.truncate_content(content)
                
                completion = await self.client.beta.chat.completions.parse(
                    model="gpt-4.1-mini",
                    max_tokens=2000,  # Increased from 1000
                    temperature=0.0,  # Lower temperature for more consistent output
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_RECIPE_EXTRACTION},
                        {"role": "user", "content": content}
                    ],
                    response_format=DishModel,
                )
                
                return url_id, completion.choices[0].message.parsed
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Extraction failed for URL {url_id}: {error_msg}")
                
                # Log specific error types for debugging
                if "content filter" in error_msg.lower():
                    logger.warning(f"Content filter rejection for URL {url_id}")
                elif "length limit" in error_msg.lower():
                    logger.warning(f"Token limit exceeded for URL {url_id}")
                elif "validation error" in error_msg.lower():
                    logger.warning(f"Validation error for URL {url_id}: {error_msg}")
                
                return url_id, None

    def save_dish(self, url_id, dish):
        """Save dish data to database"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Save main dish info (added date_published and date_updated, removed cooking_technique)
                dish_fields = [
                    'dish_name', 'description', 'meal_time', 'general_category', 
                    'specific_category', 'cuisine', 'complexity', 'serving_temperature', 
                    'season', 'source', 'star_rating', 'num_ratings', 
                    'num_reviews', 'date_published', 'date_updated'
                ]
                values = []
                for field in dish_fields:
                    if field == 'source':
                        values.append('recipe')  # Hardcoded source
                    else:
                        values.append(getattr(dish, field, None))
                
                cursor.execute(f"""
                    INSERT INTO recipe.dishes (dish_id, {', '.join(dish_fields)})
                    VALUES (%s, {', '.join(['%s'] * len(dish_fields))})
                    ON CONFLICT (dish_id) DO UPDATE SET
                    {', '.join([f'{field} = EXCLUDED.{field}' for field in dish_fields])},
                    date_modified = CURRENT_TIMESTAMP
                """, [url_id] + values)
                
                # Save ingredients with both ingredient and flavor_ingredient fields
                if dish.ingredients:
                    cursor.execute("DELETE FROM recipe.dish_ingredients WHERE dish_id = %s", (url_id,))
                    for ingredient in dish.ingredients:
                        cursor.execute("""
                            INSERT INTO recipe.dish_ingredients 
                            (dish_id, ingredient, flavor_ingredient, format, prep_method, quantity, units, type,
                            ingredient_role, flavor_role, alternative_ingredients)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (url_id, 
                            getattr(ingredient, 'ingredient', None),  # Full ingredient name
                            getattr(ingredient, 'flavor_ingredient', None),  # Flavor-contributing ingredient
                            ingredient.format, ingredient.prep_method,
                            ingredient.quantity, ingredient.units, ingredient.type, 
                            ingredient.ingredient_role, ingredient.flavor_role,
                            ingredient.alternative_ingredients))
                
                # Save attributes
                if dish.attributes:
                    attrs = dish.attributes
                    cursor.execute("""
                        INSERT INTO recipe.dish_attributes 
                        (dish_id, flavor_attributes, texture_attributes, aroma_attributes, cooking_techniques,
                        diet_preferences, functional_health, occasions, convenience_attributes,
                        social_setting, emotional_attributes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (dish_id) DO UPDATE SET
                        flavor_attributes = EXCLUDED.flavor_attributes,
                        texture_attributes = EXCLUDED.texture_attributes,
                        aroma_attributes = EXCLUDED.aroma_attributes,
                        cooking_techniques = EXCLUDED.cooking_techniques,
                        diet_preferences = EXCLUDED.diet_preferences,
                        functional_health = EXCLUDED.functional_health,
                        occasions = EXCLUDED.occasions,
                        convenience_attributes = EXCLUDED.convenience_attributes,
                        social_setting = EXCLUDED.social_setting,
                        emotional_attributes = EXCLUDED.emotional_attributes
                    """, (url_id, attrs.flavor_attributes, attrs.texture_attributes,
                        attrs.aroma_attributes, attrs.cooking_techniques, attrs.diet_preferences,
                        attrs.functional_health, attrs.occasions,
                        attrs.convenience_attributes, attrs.social_setting,
                        attrs.emotional_attributes))
                
                conn.commit()

    async def run(self):
        """Main processing loop"""
        logger.info("Starting recipe extraction")
        
        while True:
            recipes = self.get_pending_recipes()
            if not recipes:
                logger.info("No recipes to process, waiting...")
                await asyncio.sleep(10)
                continue
            
            logger.info(f"Processing {len(recipes)} recipes")
            
            # Extract all recipes concurrently
            tasks = [self.extract_recipe(recipe) for recipe in recipes]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Save successful extractions and update status
            successful = 0
            failed = 0
            for result in results:
                if isinstance(result, tuple) and len(result) == 2:
                    url_id, dish = result
                    if dish:
                        try:
                            self.save_dish(url_id, dish)
                            self.update_llm_status(url_id, 'complete')
                            successful += 1
                        except Exception as e:
                            logger.error(f"Failed to save dish {url_id}: {e}")
                            self.update_llm_status(url_id, 'failed', str(e))
                            failed += 1
                    else:
                        self.update_llm_status(url_id, 'failed', 'OpenAI extraction failed')
                        failed += 1
                else:
                    # Handle exceptions from gather
                    logger.error(f"Unexpected result type: {result}")
                    failed += 1
            
            logger.info(f"Successfully processed {successful}/{len(recipes)} recipes ({failed} failed)")


async def main():
    extractor = RecipeExtractor(batch_size=64, max_concurrency=16)
    await extractor.run()


if __name__ == "__main__":
    asyncio.run(main())