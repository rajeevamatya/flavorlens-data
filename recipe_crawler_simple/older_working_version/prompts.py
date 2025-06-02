from typing import List, Union
from pydantic import BaseModel, Field, ConfigDict


class FlavorIntensity(BaseModel):
    sweetness: int = Field(
        None, 
        description="Intensity of sweetness on a scale from 0-10."
    )
    sourness: int = Field(
        None, 
        description="Intensity of sourness on a scale from 0-10."
    )
    bitterness: int = Field(
        None, 
        description="Intensity of bitterness on a scale from 0-10."
    )
    umami: int = Field(
        None, 
        description="Intensity of umami flavor on a scale from 0-10."
    )
    saltiness: int = Field(
        None, 
        description="Intensity of saltiness on a scale from 0-10."
    )
    richness: int = Field(
        None, 
        description="Intensity of richness on a scale from 0-10."
    )

class FlavorProfile(BaseModel):
    flavors: Union[List[str], None] = Field(
        None, 
        description="Primary flavor notes experienced in the dish (e.g., salty, sweet, spicy). Null if not specified."
    )
    aroma: Union[List[str], None] = Field(
        None, 
        description="Distinctive scents and smells associated with the dish. Null if not specified."
    )
    mouthfeel: Union[List[str], None] = Field(
        None, 
        description="Textural qualities experienced when eating the dish (e.g., crispy, creamy, smooth). Null if not specified."
    )
    intensity: Union[FlavorIntensity, None] = Field(
        None, 
        description="Detailed breakdown of flavor intensity for various taste dimensions. "
    )


class Dish(BaseModel):
    name: str = Field(
        ..., 
        description="The official or common name of the dish."
    )
    category: Union[str, None] = Field(
        None, 
        description="The type of meal or course the dish belongs to (e.g., Main Course, Appetizer, Dessert). Null if not specified."
    )
    cuisines: Union[List[str], None] = Field(
        None, 
        description="Cuisines associated with the dish, e.g. Italian, American, Chinese. Null if not specified."
    )
    ingredients: Union[List[str], None] = Field(
        None, 
        description="Extract base ingredients by removing any descriptors and modifiers (e.g., green vegetables, black pepper, chicken, parmesan cheese, flour, etc.). Ensure each ingredient is a noun itself. Null if not specified."
    )
    cooking_techniques: Union[List[str], None] = Field(
        None, 
        description="Specific culinary techniques used in preparing the dish. Null if not specified."
    )
    preparation_techniques: Union[List[str], None] = Field(
        None, 
        description="Preparatory methods used before cooking the dish. Null if not specified."
    )
    serving_temperature: Union[str, None] = Field(
        None, 
        description="The recommended temperature at which the dish should be served (e.g., Hot, Warm, Cold, Frozen). Null if not specified."
    )
    dietary_preferences: Union[List[str], None] = Field(
        None, 
        description="Dietary preferences, classifications or restrictions for the dish (e.g., Vegetarian, Non-Vegetarian, Vegan). Null if not specified."
    )
    seasonality: Union[str, None] = Field(
        None, 
        description="The season (Summer, Winter, Spring, Autumn) when the dish is typically prepared or most appropriate. Null if not specified."
    )

class ConsumerInsight(BaseModel): 
    nutrition_labels: Union[List[str], None] = Field(
        None, 
        description="Nutritional characterizations or health-related labels for the dish (e.g., Low-Sodium, High-Protein, Gluten-Free, Low-Carb, Heart-Healthy). Null if not specified."
    )
    convenience_labels: Union[List[str], None] = Field(
        None, 
        description="Labels indicating the ease of preparation or consumption (e.g., Quick-Prep, One-Pot, Freezer-Friendly, Meal-Prep, Ready-in-15, Microwave-Safe). Null if not specified."
    )
    sustainability_labels: Union[List[str], None] = Field(
        None, 
        description="Environmental and ethical labels related to the dish's production, ingredients, or preparation (e.g., Locally-Sourced, Farm-to-Table, Zero-Waste, Plant-Based, Organic, Fair-Trade). Null if not specified."
    )
    events_and_occasions: Union[List[str], None] = Field(
        None, 
        description="Events and occasional the recipe is to be used on. Null if not specified."
    )
    equipments: Union[List[str], None] = Field(
        None, 
        description="Equipments used in the recipe. Null if not specified."
    )
    brands: Union[List[str], None] = Field(
        None, 
        description="Brands mentioned in the recipe. Null if not specified."
    )


class Metadata(BaseModel):
    publication_date: Union[str, None] = Field(
        None, 
        description="The date when the recipe was first published or recorded. Null if not specified."
    )
    update_date: Union[str, None] = Field(
        None, 
        description="The most recent date when the recipe information was updated. Null if not specified."
    )
    star_rating: Union[float, None] = Field(
        None, 
        description="The recipe's rating as a numerical value from 1-5 (e.g., 4, 4.5, etc.). Null if not specified."
    )
    ratings_count: Union[int, None] = Field(
        None, 
        description="The total number of ratings for the recipe. Null if not specified."
    )
    reviews_count: Union[int, None] = Field(
        None, 
        description="The total number of reviews for the recipe. Null if not specified."
    )
    times_shared: Union[int, None] = Field(
        None, 
        description="The total number of times the recipe has been shared. Null if not specified."
    )
    preparation_level: Union[str, None] = Field(
        None, 
        description="The complexity or skill level required to prepare the dish (e.g., Beginner, Intermediate, Advanced). Null if not specified."
    )

class RecipeDishModel(BaseModel):
    dish: Dish = Field(
        ..., 
        description="Detailed information about the specific dish."
    )
    consumer_insight: Union[ConsumerInsight, None] = Field(
        None, 
        description="Consumer-facing insights about the recipe. Null if not specified."
    )
    metadata: Union[Metadata, None] = Field(
        None, 
        description="Contextual and administrative metadata about the recipe. Null if not specified."
    )
    flavor_profile: Union[FlavorProfile, None] = Field(
        None, 
        description="A detailed analysis of the dish's flavor characteristics. Null if not specified."
    )

class MenuDishModel(BaseModel):
    dish: Dish = Field(
        ..., 
        description="Detailed information about the specific dish."
    )
    flavor_profile: Union[FlavorProfile, None] = Field(
        None, 
        description="A detailed analysis of the dish's flavor characteristics. Null if not specified."
    )
  

  # from typing import List, Optional
# from pydantic import BaseModel, Field
# import enum


# SYSTEM_PROMPT = """
# Extract the information from the recipe as per the provided JSON schema.
# Guidelines:
# 1. For ingredient and alternative_ingredients, extract ingredients without unnecessary modifiers (e.g., chicken, salt, black pepper, parmesan cheese, jalapeno jam, lemon-garlic butter, etc)
# 2. processing_method should focus on techniques that intensify taste and aroma (e.g., roasted, fermented, aged, smoked, caramerlized, honey-braised, etc.)
#     Exclude non-flavor-related methods like chopping, peeling, or removing skin. should be a one to two-word term. Output null if not specified. Do not infer.
# 3. other_attributes of ingredient must relate to flavor, aroma, nutrition, or sustainability and must be strictly one-word, (e.g., unsweetened, low-sodium,
# low-fat, cage-free, organic, gluten-free). Output null if not specified. Do not infer.
# 4. In general, prioritize clarity and minimal verbosity. Remove redundant or decorative language. Focus on essential ingredient characteristics.
# """

# class MealPeriod(enum.Enum):
#   BREAKFAST = "Breakfast"
#   LUNCH = "Lunch"
#   DINNER = "Dinner"
#   LATE_NIGHT = "Late-night"
#   ALL_DAY = "All-day"
#   SNACK = "Snack"

#   def __repr__(self):
#         return self.value

# class MenuCategory(enum.Enum):
#   APPETIZER = "Appetizer"
#   ENTREE = "Entree"
#   DESSERT = "Dessert"
#   SIDE = "Side"
#   SNACK = "Snack"
#   BEVERAGE = "Beverage"

#   def __repr__(self):
#         return self.value

# class Season(enum.Enum):
#   SUMMER = "Summer"
#   WINTER = "Winter"
#   AUTUMN = "Autumn"
#   SPRING = "Spring"

#   def __repr__(self):
#         return self.value

# class Ingredient(BaseModel):
#     name: str = Field(..., description="""Ingredient without unnecessary modifiers(e.g., chicken, salt, black pepper, parmesan cheese, jalapeno jam, lemon-garlic butter, etc)""")

#     processing_method: Optional[str] = Field(
#         None, description="""Flavor-enhancing processing method applied to the ingredient (e.g., roasted, fermented, aged, smoked, caramelized,
#         honey-braised, etc.). Give careful consideration to modifers such as in honey-braised, oven-roasted, etc. Must be a one to two-word term.
#         Excludes non-flavor-related methods like chopped, peeled, or removing skin."""
#     )
#     other_attributes: Optional[List[str]] = Field(
#         None, description="Additional attributes of the ingredient. Must be one-word term (e.g., unsweetened, low-sodium, low-fat, cage-free, organic, gluten-free). Null if not specified."
#     )
#     alternative_ingredients: Optional[List[str]] = Field(
#         None, description="Alternative ingredients without unnecessary modifiers. Must be explicitly mentioned, e.g., chicken, salt, black pepper, parmesan cheese. Null if not specified."
#     )


# class FlavorIntensity(BaseModel):
#     sweetness: Optional[int] = Field(
#         None, description="Degree of sweetness perceived in the dish, rated from 0-10, 10 being the highest."
#     )
#     sourness: Optional[int] = Field(
#         None, description="Degree of sourness perceived in the dish, rated from 0-10, 10 being the highest."
#     )
#     bitterness: Optional[int] = Field(
#         None, description="Degree of bitterness perceived in the dish, rated from 0-10, 10 being the highest."
#     )
#     umami: Optional[int] = Field(
#         None, description="Degree of umami perceived in the dish, rated from 0-10, 10 being the highest."
#     )
#     saltiness: Optional[int] = Field(
#         None, description="Degree of saltiness perceived in the dish, rated from 0-10, 10 being the highest."
#     )
#     richness: Optional[int] = Field(
#         None, description="Degree of richness perceived in the dish, rated from 0-10, 10 being the highest."
#     )


# class FlavorProfile(BaseModel):
#     flavors: Optional[List[str]] = Field(
#         None, description="Descriptors capturing the dominant flavors of the dish (e.g., salty, sweet, spicy, vanilla, etc)."
#     )
#     aroma: Optional[List[str]] = Field(
#         None, description="Descriptors capturing the aromatic characteristics of the dish (e.g. smoky, nutty, garlicky, etc.)"
#     )
#     mouthfeel: Optional[List[str]] = Field(
#         None, description="Descriptors capturing the textural experience of the dish (e.g., crispy, creamy, smooth)."
#     )
#     # intensity: FlavorIntensity = Field(
#     #     None, description="Breakdown of perceived taste intensities for the dish."
#     # )


# class Dish(BaseModel):
#     name: str = Field(..., description="The official or commonly recognized name of the dish. Keep it short.")
#     dish_type: str = Field(..., description="Specific type of prepared food or beverage, representing the distinct culinary classification of the item (e.g., Pizza, Pasta, Burger, Chicken Dish, Chicken Wings, Cake, Smoothie, Cocktail, etc).")
#     category: MenuCategory = Field(..., description="Culinary classification indicating dish's role in a meal")
#     serving_time: List[MealPeriod] = Field(..., description="Typical meal periods when the dish is traditionally consumed.")
#     cuisines: Optional[List[str]] = Field(
#         None, description="Cuisines associated with the dish (e.g., Italian, American, Chinese)."
#     )
#     cooking_techniques: Optional[List[str]] = Field(
#         None, description="Culinary techniques applied during the cooking process. Must be a one to two-word term (e.g., grilled, sautéed, oven-roasted, honey-braised etc.). Null if not specified. Do not infer."
#     )
#     preparation_techniques: Optional[List[str]] = Field(
#         None, description="Preparation techniques used before cooking. Must be a one to two-word term (e.g., marinated, fermented, infused, etc.). Null if not specified. Do not infer."
#     )

#     popular_pairings: Optional[List[str]] = Field(
#         None, description="Foods or beverages that are frequently paired with the dish. Null if not specified."
#     )
#     dietary_preferences: Optional[List[str]] = Field(
#         None, description="Dietary classifications applicable to the dish (e.g., Vegetarian, Vegan, Gluten-Free, Keto, etc). Null if not specified."
#     )
#     seasonality: Optional[List[Season]] = Field(
#         None, description="Season when the dish is typically consumed or prepared. Null if not specified."
#     )
#     keywords: Optional[List[str]] = Field(
#         None, description="Any nutrition, convenience, sustainability, event, or occasion related keywords. Each keywods must be a single word (e.g., low-sodium, quick-prep, farm-to-table, family-meal, etc). Null if not specified."
#     )


# class Metadata(BaseModel):
#     publication_date: Optional[str] = Field(
#         None, description="Original publication date of the recipe."
#     )
#     update_date: Optional[str] = Field(
#         None, description="Most recent update date for the recipe."
#     )
#     star_rating: Optional[float] = Field(
#         None, description="Overall start rating of the recipe on a scale from 1 to 5."
#     )
#     ratings_count: Optional[int] = Field(
#         None, description="Total number of ratings given to the recipe."
#     )
#     reviews_count: Optional[int] = Field(
#         None, description="Total number of reviews written for the recipe."
#     )


# class RecipeDishModel(BaseModel):
#     dish: Dish = Field(..., description="Core details about the dish described in the recipe.")
#     ingredients: List[Ingredient] = Field(..., description="Comprehensive list of ingredients used in the recipe.")
#     metadata: Optional[Metadata] = Field(
#         None, description="Metadata providing contextual details about the recipe."
#     )
#     flavor_profile: FlavorProfile = Field(
#         ..., description="Flavor characteristics of the dish as captured in the recipe."
#     )


# class MenuDishModel(BaseModel):
#     dish: Dish = Field(..., description="Core details about the menu item.")
#     ingredients: List[Ingredient] = Field(..., description="Comprehensive list of ingredients used in the menu item.")
#     flavor_profile: FlavorProfile = Field(
#         ..., description="Flavor characteristics of the menu item based on the menu description."
#     )
#     # popularity_score: Optional[float] = Field(
#     #     None, description="Measure of dish popularity, rated on a scale from 0-5."
#     )







# SYSTEM_PROMPT_RECIPE_EXTRACTION = """
# You are an expert in recipe analysis and data extraction. Your task is to parse recipes and extract 
# structured data according to the provided JSON schema. If the input contains more than one recipe, 
# only extract data for the first recipe.
# Follow these guidelines:

# 1. For valid recipe items:
#    - Extract all relevant details matching the JSON schema.
#    - Maintain consistency in formatting and data types.
#    - Preserve exact ingredient names and cooking methods as written (when possible).
#    - Use null for missing or uncertain values.

# 2. For invalid or non-recipe inputs:
#    - Return an empty JSON object: {}
#    - Do not attempt to extract partial data.

# Ensure that all extracted data strictly adheres to the JSON schema structure and data type requirements.
# """

# RESPONSE_FORMAT_RECIPE_EXTRACTION = {
#     "type": "json_schema",
#     "json_schema": {
#         "name": "recipe",
#         "strict": True,
#         "schema": {
#             "type": "object",
#             "properties": {
#                 "dish_name": {
#                     "type": "string",
#                     "description": "A simplified name for the dish without unnecessary wording (e.g., Chicken Parmesan instead of 'Delicious Chicken Parmesan with Extra Yummy Cheese')."
#                 },
#                 "publication_date": {
#                     "type": ["string", "null"],
#                     "description": "The original publication date of the recipe (format: yyyy-mm-dd). If none, set to null."
#                 },
#                 "updated_date": {
#                     "type": ["string", "null"],
#                     "description": "The date the recipe was last updated (format: yyyy-mm-dd). If none, set to null."
#                 },
#                 "rating": {
#                     "type": ["number", "null"],
#                     "description": "The recipe’s rating as a numerical value (e.g., 4, 4.5, etc.). If none, set to null."
#                 },
#                 "ratings_count": {
#                     "type": ["number", "null"],
#                     "description": "The total number of ratings for the recipe. If none, set to null."
#                 },
#                 "reviews_count": {
#                     "type": ["number", "null"],
#                     "description": "The total number of reviews for the recipe. If none, set to null."
#                 },
#                 "times_shared": {
#                     "type": ["number", "null"],
#                     "description": "The total number of times the recipe has been shared. If none, set to null."
#                 },
#                 "course": {
#                     "type": "string",
#                     "description": "The course of the meal (e.g., starters, mains, desserts, beverages)."
#                 },
#                 "category": {
#                     "type": "string",
#                     "description": "A specific category for the dish (e.g., salad, pasta, cocktail, etc.)."
#                 },
#                 "ingredients": {
#                     "type": "array",
#                     "description": "List of ingredients without quantities, explicitly mentioned in the recipe. The ingredients may contain modifier related to cooking techniques. Do not infer ingredients. (e.g. grilled chicken, unsalted butter, granulated sugar, baking powder, salt, heavy cream, cocoa powder, almond extract, honey, olive oil, soy sauce, etc.)",
#                     "items": {
#                         "type": "string"
#                     }
#                 },
#                 "alternative_ingredients": {
#                     "type": ["array", "null"],
#                     "description": "List of ingredients witout quantities, explicitly mentioned as alternatives in the recipe. Do not infer ingredients (e.g., gin, chives, almond, etc.). If none, set to null.",
#                     "items": {
#                         "type": "string"
#                     }
#                 },
#                 "flavor_and_texture": {
#                     "type": ["array", "null"],
#                     "description": "Flavor profiles and textures mentioned or inferred (e.g., tangy, crispy). If none, set to null.",
#                     "items": {
#                         "type": "string"
#                     }
#                 },
#                 "cooking_technique": {
#                     "type": ["array", "null"],
#                     "description": "Cooking methods explicitly mentioned (e.g., grilled, oven-roasted, simmered, charbroiled, sous vide, slow-cooked, air-fried, one-pot, etc). If none, set to null.",
#                     "items": {
#                         "type": "string"
#                     }
#                 },
#                 "brand": {
#                     "type": ["array", "null"],
#                     "description": "Brand names explicitly mentioned. If none, set to null.",
#                     "items": {
#                         "type": "string"
#                     }
#                 },
#                 "preparation_level": {
#                     "type": ["string", "null"],
#                     "description": "The difficulty level of the recipe (e.g., Easy, Intermediate, Advanced). If none, set to null."
#                 },
#                 "total_time": {
#                     "type": ["number", "null"],
#                     "description": "Total time in minutes for preparation and cooking. If none, set to null."
#                 },
#                 "cultural_reference": {
#                     "type": ["array", "null"],
#                     "description": "Cuisine, cultural or regional associations (e.g., Italian, Indian, Chinese, Country, Southern, etc.). If none, set to null.",
#                     "items": {
#                         "type": "string"
#                     }
#                 },
#                 "seasonality": {
#                     "type": ["array", "null"],
#                     "description": "Season or holiday associations (e.g., Winter, Thanksgiving). If none, set to null.",
#                     "items": {
#                         "type": "string"
#                     }
#                 },
#                  "themes": {
#                     "type": ["array", "null"],
#                     "description": "Theme associations (e.g., party and gathering, comfort food, holiday meal, quick and easy recipe, kid-friendly, meal-prep and freezer friendly, etc. ). If none, set to null.",
#                     "items": {
#                         "type": "string"
#                     }
#                 },
#                 "dietary_labels": {
#                     "type": ["array", "null"],
#                     "description": "Dietary accommodations explicitly mentioned (e.g., vegetarian, vegan, gluten-free, paleo, halal, kosher, etc ). If none, set to null.",
#                     "items": {
#                         "type": "string"
#                     }
#                 },
#                 "health_labels": {
#                     "type": ["array", "null"],
#                     "description": "Health-related characteristics (e.g., low-calorie, high-protein, zero-sugar). If none, set to null.",
#                     "items": {
#                         "type": "string"
#                     }
#                 },
#                 "sustainability_labels": {
#                     "type": ["array", "null"],
#                     "description": "Environmental and sourcing attributes (e.g., organic, grass-fed, cage-free, GMO-free, etc.). If none, set to null.",
#                     "items": {
#                         "type": "string"
#                     }
#                 },
#                 "convenience_labels": {
#                     "type": ["array", "null"],
#                     "description": "Convenience labels (e.g., Quick, Meal Prep, One-pot, etc.). If none, set to null.",
#                     "items": {
#                         "type": "string"
#                     }
#                 }
#             },
#             "required": [
#                 "dish_name", "publication_date", "updated_date", "rating", "ratings_count",
#                 "reviews_count", "times_shared", "course", "category", "ingredients",
#                 "alternative_ingredients", "flavor_and_texture", "cooking_technique",
#                 "brand", "preparation_level", "total_time", "cultural_reference", "seasonality", "themes",
#                 "dietary_labels", "health_labels", "sustainability_labels", "convenience_labels"
#             ],
#             "additionalProperties": False
#         }
#     }
# }
