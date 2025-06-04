# Updated Menu Processor (openai_menu_processor.py)
import logging
import asyncio
from openai import AsyncAzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config import AZURE_API_ENDPOINT, AZURE_API_KEY, AZURE_API_VERSION, setup_logging, get_db_connection
from menu_processor_simple.menu_prompts import SYSTEM_PROMPT_MENU_EXTRACTION, DishModel

setup_logging()
logger = logging.getLogger(__name__)


class MenuProcessor:
    def __init__(self, batch_size=32, max_concurrency=8):
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.client = AsyncAzureOpenAI(
            api_key=AZURE_API_KEY, 
            api_version="2024-12-01-preview", 
            azure_endpoint="https://locmatic-menu-recipe.openai.azure.com/",
            timeout=60.0,
        )

    def get_pending_menus(self):
        """Get menu items that need extraction"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """SELECT item_id, name, description, category, date_uploaded
                       FROM menu.demo_menu_items 
                       WHERE llm_status = 'pending'
                         AND description IS NOT NULL
                         AND description != ''
                       ORDER BY date_uploaded DESC LIMIT %s""",
                    (self.batch_size,)
                )
                return cursor.fetchall()

    def update_llm_status(self, item_id, status, failure_reason=None):
        """Update LLM processing status"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE menu.demo_menu_items 
                    SET llm_status = %s, llm_error_reason = %s
                    WHERE item_id = %s
                """, (status, failure_reason, item_id))
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
    async def extract_menu_item(self, menu_data):
        """Extract structured menu data using OpenAI"""
        item_id, name, description, category, date_uploaded = menu_data
        
        async with self.semaphore:
            try:
                # Format content as: "Name (Category): Description"
                # Handle missing fields gracefully
                name_part = name or "Unknown Dish"
                category_part = f" ({category})" if category else ""
                description_part = f": {description}" if description else ""
                
                content = f"{name_part}{category_part}{description_part}"
                content = self.truncate_content(content)
                
                completion = await self.client.beta.chat.completions.parse(
                    model="gpt-4.1-mini",
                    max_tokens=2000,
                    temperature=0.0,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_MENU_EXTRACTION},
                        {"role": "user", "content": content}
                    ],
                    response_format=DishModel,
                )
                
                return item_id, completion.choices[0].message.parsed, date_uploaded
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Extraction failed for menu item {item_id}: {error_msg}")
                
                # Log specific error types for debugging
                if "content filter" in error_msg.lower():
                    logger.warning(f"Content filter rejection for item {item_id}")
                elif "length limit" in error_msg.lower():
                    logger.warning(f"Token limit exceeded for item {item_id}")
                elif "validation error" in error_msg.lower():
                    logger.warning(f"Validation error for item {item_id}: {error_msg}")
                
                return item_id, None, date_uploaded

    def save_dish(self, item_id, dish, date_uploaded):
        """Save dish data to menu database"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Save main dish info - handle menu-specific vs recipe-specific fields
                menu_fields = [
                    'dish_name', 'description', 'meal_time', 'general_category', 
                    'specific_category', 'cuisine', 'serving_temperature', 
                    'season', 'source'
                ]
                values = []
                for field in menu_fields:
                    if field == 'source':
                        values.append('menu')  # Hardcoded source for menu items
                    else:
                        values.append(getattr(dish, field, None))
                
                # Add default values for recipe-specific fields not available in menus
                values.extend([
                    None,  # complexity
                    None,  # star_rating
                    0,     # num_ratings  
                    0,     # num_reviews
                    date_uploaded.date() if date_uploaded else None,  # date_published (from date_uploaded)
                    None   # date_updated
                ])
                
                all_fields = menu_fields + ['complexity', 'star_rating', 'num_ratings', 'num_reviews', 'date_published', 'date_updated']
                
                cursor.execute(f"""
                    INSERT INTO menu.dishes (dish_id, {', '.join(all_fields)})
                    VALUES (%s, {', '.join(['%s'] * len(all_fields))})
                    ON CONFLICT (dish_id) DO UPDATE SET
                    {', '.join([f'{field} = EXCLUDED.{field}' for field in menu_fields])},
                    date_modified = CURRENT_TIMESTAMP
                """, [item_id] + values)
                
                # Save ingredients - handle fields that may not exist in menu prompts
                if dish.ingredients:
                    cursor.execute("DELETE FROM menu.dish_ingredients WHERE dish_id = %s", (item_id,))
                    for ingredient in dish.ingredients:
                        cursor.execute("""
                            INSERT INTO menu.dish_ingredients 
                            (dish_id, ingredient, flavor_ingredient, format, prep_method, quantity, units, type,
                            ingredient_role, flavor_role, alternative_ingredients)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (item_id, 
                            getattr(ingredient, 'ingredient', None),
                            getattr(ingredient, 'flavor_ingredient', None),
                            getattr(ingredient, 'format', None),
                            getattr(ingredient, 'prep_method', None),
                            None,  # quantity - not available in menu prompts
                            None,  # units - not available in menu prompts
                            getattr(ingredient, 'type', None),
                            getattr(ingredient, 'ingredient_role', None),
                            getattr(ingredient, 'flavor_role', None),
                            getattr(ingredient, 'alternative_ingredients', None)))
                
                # Save attributes
                if dish.attributes:
                    attrs = dish.attributes
                    cursor.execute("""
                        INSERT INTO menu.dish_attributes 
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
                    """, (item_id, attrs.flavor_attributes, attrs.texture_attributes,
                        attrs.aroma_attributes, attrs.cooking_techniques, attrs.diet_preferences,
                        attrs.functional_health, attrs.occasions,
                        attrs.convenience_attributes, attrs.social_setting,
                        attrs.emotional_attributes))
                
                conn.commit()

    async def run(self):
        """Main processing loop"""
        logger.info("Starting menu extraction")
        
        while True:
            menu_items = self.get_pending_menus()
            if not menu_items:
                logger.info("No menu items to process, waiting...")
                await asyncio.sleep(10)
                continue
            
            logger.info(f"Processing {len(menu_items)} menu items")
            
            # Extract all menu items concurrently
            tasks = [self.extract_menu_item(item) for item in menu_items]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Save successful extractions and update status
            successful = 0
            failed = 0
            for result in results:
                if isinstance(result, tuple) and len(result) == 3:
                    item_id, dish, date_uploaded = result
                    if dish:
                        try:
                            self.save_dish(item_id, dish, date_uploaded)
                            self.update_llm_status(item_id, 'complete')
                            successful += 1
                        except Exception as e:
                            logger.error(f"Failed to save dish {item_id}: {e}")
                            self.update_llm_status(item_id, 'failed', str(e))
                            failed += 1
                    else:
                        self.update_llm_status(item_id, 'failed', 'OpenAI extraction failed')
                        failed += 1
                else:
                    # Handle exceptions from gather
                    logger.error(f"Unexpected result type: {result}")
                    failed += 1
            
            logger.info(f"Successfully processed {successful}/{len(menu_items)} menu items ({failed} failed)")


async def main():
    processor = MenuProcessor(batch_size=64, max_concurrency=16)
    await processor.run()


if __name__ == "__main__":
    asyncio.run(main())