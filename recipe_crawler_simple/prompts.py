# Updated Pydantic Models (prompts.py)
from typing import List, Optional, Union
from pydantic import BaseModel, field_validator
from decimal import Decimal
from enum import Enum
from datetime import date
import re


class MealTime(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    DESSERT = "dessert"


class GeneralCategory(str, Enum):
    BEVERAGE = "beverage"
    DESSERT = "dessert"
    SAUCE_CONDIMENT = "sauce/condiment"
    MAIN_DISH = "main dish"
    SNACK = "snack"
    BAKERY = "bakery"
    APPETIZER_SIDE_DISH = "appetizer/side"
    CONFECTIONERY = "confectionery"


class Season(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    ALL_SEASON = "all-season"


class Complexity(str, Enum):
    EASY = "easy"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ServingTemperature(str, Enum):
    HOT = "hot"
    WARM = "warm"
    ROOM = "room"
    COLD = "cold"
    ICED = "iced"
    FROZEN = "frozen"


class IngredientRole(str, Enum):
    BASE = "base"
    FUNCTIONAL = "functional"
    FLAVOR_AROMATIC = "flavor/aromatic"
    TEXTURE = "texture"


class FlavorRole(str, Enum):
    DOMINANT = "dominant"
    SUPPORTIVE = "supportive"
    ACCENT = "accent"
    BACKGROUND = "background"
    CONTRASTING = "contrasting"


class PhysicalFormat(str, Enum):
   POWDER = "powder"
   FLAKES = "flakes"
   GROUND = "ground"
   WHOLE_SPICE = "whole spice"
   DRIED = "dried"
   GRANULATED = "granulated"
   OIL = "oil"
   JUICE = "juice"
   MILK = "milk"
   CONDENSED_MILK = "condensed milk"
   BROTH = "broth"
   STOCK = "stock"
   SYRUP = "syrup"
   VINEGAR = "vinegar"
   EXTRACT = "extract"
   SAUCE = "sauce"
   BRINE = "brine"
   PASTE = "paste"
   PUREE = "puree"
   CONCENTRATE = "concentrate"
   CREAM = "cream"
   SPREAD = "spread"
   JAM_PRESERVE = "jam_preserve"
   JELLY = "jelly"
   BUTTER = "butter"
   FROZEN = "frozen"
   CANNED = "canned"
   ZEST = "zest"
   PEEL = "peel"
   SEEDS = "seeds"
   PULP = "pulp"
   RAW_UNPROCESSED = "raw or unprocessed"


SYSTEM_PROMPT_RECIPE_EXTRACTION = """
You are a recipe attribute extractor. Extract the following data from the provided recipe content:

IMPORTANT INSTRUCTIONS:
- First, check if the provided content is actually a recipe or cooking instructions. If not, return null for all fields.
- Provide ALL extracted information in English and roman script (no accent or umlauts) only. Translate any non-English content to English.
- For quantities, use ONLY numeric values (e.g., 2, 1.5, 0.25). If you see ranges like "1-3" or "2 to 4", use the first/lower number.
- If a quantity is unclear or not specified, set it to null.

DISH INFORMATION:
1. dish_name: The official or common name of the dish
2. description: Brief description of the dish (max 200 characters)
3. meal_time: Time of day when the dish is typically consumed (breakfast, lunch, dinner, snack, dessert)
4. general_category: Broad classification of the dish (beverage, dessert, sauce/condiment, main dish, snack, bakery, appetizer/side, confectionery)
5. specific_category: More specific categorization within the general category (eg. tiramisu, cake, cocktail, pizza, burger, etc.)
6. cuisine: Culinary tradition or regional cuisine (e.g., Italian, Mexican, Asian, Italian-American, etc.). Do not put diet preferences such as vegan, plant-based, etc.
7. complexity: Preparation difficulty level (easy, intermediate, advanced)
8. serving_temperature: Recommended serving temperature (hot, warm, room, cold, iced, frozen)
9. season: Extract seasonal association only if explicitly mentioned in the recipe text or clearly inferred from context. If not specified, leave blank (spring, summer, fall, winter, all-season)
10. star_rating: Average rating for the dish on a scale of 0-5 (e.g. 3, 4, 4.7, 4.56, etc.)
11. num_ratings: Total number of ratings received
12. num_reviews: Total number of reviews received
13. date_published: The original publication date of the recipe on the website. Use the format yyyy-mm-dd (e.g., 2023-03-15). This should be the date when the recipe was first posted, not any subsequent update dates.
14. date_updated: The most recent date when the recipe content was modified or updated. Use the format yyyy-mm-dd (e.g., 2024-01-20). 

INGREDIENTS (for each ingredient):
1. ingredient: Full ingredient name including all descriptors, formats, modifiers, parts, brands, preparation states, preparation methods, cutting methods, and 
                dietary preferences (e.g. matcha green tea powder, extra-virgin olive oil, bone-in pork chops, vegan cheddar cheese, freeze dried raspberries, etc.)

2. flavor_ingredient:  Extract the ingredient that provides flavor from each ingredient name. If the ingredient has minimal flavor, extract the base ingredient itself. 
                        Always extract something. Examples: "matcha green tea" → matcha, "coconut sugar" → coconut, "coconut oil" → coconut oil, "olive oil" → olive oil, 
                        "vanilla extract" → vanilla, "white chocolate chips" → white chocolate, "vegetable shortening" → vegetable, "grated parmesan cheese" → parmesan cheese, 
                        "melted mozzarella"  → mozzarella cheese, "vegan almond milk" → almond, "maple syrup" → maple, "tomato paste" → tomato, "black pepper" → black pepper,  
                        "steel cut oats" → oats, "water" → water

3. format: Physical processing form that affects the ingredient's flavor, texture, or cooking behavior (e.g., powder, flakes, ground, whole spice, dried, granulated, oil, juice, 
            milk, condensed milk, broth, stock, syrup, vinegar, extract, sauce, brine, paste, puree, concentrate, cream, spread, jam_preserve, jelly, butter, frozen, canned, zest, 
            peel, seeds, pulp, unprocessed, other). Choose "unprocessed" for fresh/raw ingredients in their natural state. Choose "other" only if the format doesn't fit any available option.

4. prep_method: Single-word or hyphenated adjective explicitly mentioned that enhance the ingredient's flavor (e.g., roasted, smoked, pickled, fermented, 
                grilled, cured, aged, marinated, oven-roasted, cold-smoked, dry-aged). Must be exactly one word or hyphenated compound. Exclude all 
                cutting/sizing methods such as chopped, minced, diced, sliced, etc.

5. quantity: Amount of the ingredient needed (NUMERIC ONLY - e.g., 2, 1.5, 0.25)
6. units: Unit of measurement for the quantity. Use the singular full form (e.g., count, cup, tablespoon, gram, mililiter, etc.)
7. type: Category or type of ingredient (e.g., protein, vegetable, spice, condiment, etc.)
8. ingredient_role: Role of the ingredient in the dish (base, functional, flavor/aromatic, texture)
9. flavor_role: Flavor contribution of the ingredient (dominant, supportive, accent, background, contrasting)
10. alternative_ingredients: List of possible substitutes using the same naming format (e.g., ["avocado oil", "canola oil"], ["coconut milk", "cream"], 
                            ["rose harissa", "green harissa"])


ATTRIBUTES (extract if explicitly mentioned OR clearly inferred from the recipe text):

1. flavor_attributes: Flavor characteristics - extract from descriptive words or ingredient profiles
   Examples: "spicy curry" → ["spicy"]; recipe with jalapeños → ["spicy"]; honey-based dish → ["sweet"]

2. texture_attributes: Textural qualities - extract from cooking methods or ingredient combinations  
   Examples: "crispy fried chicken" → ["crispy"]; pasta with cream sauce → ["creamy"]; bread recipe → ["chewy", "soft"]

3. aroma_attributes: Distinctive scents - extract from aromatic ingredients or cooking techniques
   Examples: garlic + herbs → ["fragrant"]; grilled/smoked dishes → ["smoky"]; citrus ingredients → ["fresh"]

4. cooking_techniques: Single-word or hyphenated adjectives describing cooking methods applied to this ingredient that enhance flavor (e.g., grilled, stir-fried, 
                        sautéed, fermented, infused, braised, roasted, steamed, etc.). Must be exactly one word or hyphenated compound. Exclude all cutting/sizing 
                        methods such as chopped, minced, diced, sliced, etc.

5. diet_preferences: Dietary classifications - infer from ingredient restrictions or explicit labels
   Examples: no meat ingredients → ["vegetarian"]; no gluten-containing ingredients → ["gluten-free"]; explicitly labeled → ["keto", "vegan"]

6. functional_health: Health benefits - infer from ingredient properties or explicit health claims
   Examples: high-protein ingredients → ["high-protein"]; low-sodium preparation → ["low-sodium"]; antioxidant-rich ingredients → ["antioxidant-rich"]

7. occasions: Suitable events - infer from dish complexity, ingredients, or cultural context
   Examples: elaborate cake → ["celebration", "birthday"]; simple breakfast dish → ["breakfast", "everyday"]; holiday spices → ["holiday"]

8. convenience_attributes: Prep/serving factors - infer from cooking method or time requirements
   Examples: single pan used → ["one-pot"]; "prepare ahead" mentioned → ["make-ahead"]; under 30 min → ["quick-prep"]

9. social_setting: Service context - infer from portion size, presentation, or dish type
   Examples: large casserole → ["family-style"]; individual plated portions → ["formal-dining"]; finger food → ["casual", "party"]

10. emotional_attributes: Emotional associations - infer from cultural context or descriptive language
   Examples: "grandma's recipe" → ["nostalgic"]; hearty stew → ["comforting"]; childhood favorite → ["comfort-food"]

Instructions: Only include attributes you can confidently identify. Avoid generic attributes unless clearly supported by evidence.

Return the extracted information in the DishModel format. Set fields to null if not specified in the recipe content.
"""


class DishIngredient(BaseModel):
    ingredient: str
    flavor_ingredient: str
    format: Optional[PhysicalFormat] = None
    prep_method: Optional[str] = None
    quantity: Optional[Decimal] = None
    units: Optional[str] = None
    type: Optional[str] = None
    ingredient_role: Optional[IngredientRole] = None
    flavor_role: Optional[FlavorRole] = None
    alternative_ingredients: Optional[List[str]] = None

    @field_validator('quantity', mode='before')
    @classmethod
    def parse_quantity(cls, v):
        if v is None or v == "":
            return None
        
        # Convert to string for processing
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        
        if isinstance(v, str):
            # Handle ranges like "1-3", "2 to 4", "1 - 2"
            range_patterns = [
                r'^(\d+(?:\.\d+)?)\s*[-–—]\s*\d+(?:\.\d+)?',  # 1-3, 1.5-2.5
                r'^(\d+(?:\.\d+)?)\s+to\s+\d+(?:\.\d+)?',     # 2 to 4
                r'^(\d+(?:\.\d+)?)\s*-\s*\d+(?:\.\d+)?',      # 1 - 2
            ]
            
            for pattern in range_patterns:
                match = re.match(pattern, v.strip(), re.IGNORECASE)
                if match:
                    return Decimal(match.group(1))
            
            # Extract first number from string
            number_match = re.search(r'(\d+(?:\.\d+)?)', v)
            if number_match:
                return Decimal(number_match.group(1))
            
            # If no number found, return None
            return None
        
        return v


class DishAttributes(BaseModel):
    flavor_attributes: Optional[List[str]] = None
    texture_attributes: Optional[List[str]] = None
    aroma_attributes: Optional[List[str]] = None
    cooking_techniques: Optional[List[str]] = None    
    diet_preferences: Optional[List[str]] = None
    functional_health: Optional[List[str]] = None
    occasions: Optional[List[str]] = None
    convenience_attributes: Optional[List[str]] = None
    social_setting: Optional[List[str]] = None
    emotional_attributes: Optional[List[str]] = None


class DishModel(BaseModel):
    dish_name: str
    description: Optional[str] = None
    meal_time: Optional[MealTime] = None
    general_category: Optional[GeneralCategory] = None
    specific_category: Optional[str] = None
    cuisine: Optional[str] = None
    complexity: Optional[Complexity] = None
    serving_temperature: Optional[ServingTemperature] = None
    season: Optional[Season] = None
    star_rating: Optional[Decimal] = None
    num_ratings: Optional[int] = None
    num_reviews: Optional[int] = None
    date_published: Optional[date] = None
    date_updated: Optional[date] = None
    ingredients: Optional[List[DishIngredient]] = None
    attributes: Optional[DishAttributes] = None

