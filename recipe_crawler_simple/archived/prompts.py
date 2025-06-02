

SYSTEM_PROMPT_RECIPE_EXTRACTION = """
You are an expert in recipe analysis and data extraction. Your task is to parse recipes and extract 
structured data according to the provided JSON schema. If the input contains more than one recipe, 
only extract data for the first recipe.
Follow these guidelines:

1. For valid recipe items:
   - Extract all relevant details matching the JSON schema.
   - Maintain consistency in formatting and data types.
   - Preserve exact ingredient names and cooking methods as written (when possible).
   - Use null for missing or uncertain values.

2. For invalid or non-recipe inputs:
   - Return an empty JSON object: {}
   - Do not attempt to extract partial data.

Ensure that all extracted data strictly adheres to the JSON schema structure and data type requirements.
"""

RESPONSE_FORMAT_RECIPE_EXTRACTION = {
    "type": "json_schema",
    "json_schema": {
        "name": "recipe",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "dish_name": {
                    "type": "string",
                    "description": "A simplified name for the dish without unnecessary wording (e.g., Chicken Parmesan instead of 'Delicious Chicken Parmesan with Extra Yummy Cheese')."
                },
                "publication_date": {
                    "type": ["string", "null"],
                    "description": "The original publication date of the recipe (format: yyyy-mm-dd). If none, set to null."
                },
                "updated_date": {
                    "type": ["string", "null"],
                    "description": "The date the recipe was last updated (format: yyyy-mm-dd). If none, set to null."
                },
                "rating": {
                    "type": ["number", "null"],
                    "description": "The recipe’s rating as a numerical value (e.g., 4, 4.5, etc.). If none, set to null."
                },
                "ratings_count": {
                    "type": ["number", "null"],
                    "description": "The total number of ratings for the recipe. If none, set to null."
                },
                "reviews_count": {
                    "type": ["number", "null"],
                    "description": "The total number of reviews for the recipe. If none, set to null."
                },
                "times_shared": {
                    "type": ["number", "null"],
                    "description": "The total number of times the recipe has been shared. If none, set to null."
                },
                "course": {
                    "type": "string",
                    "description": "The course of the meal (e.g., starters, mains, desserts, beverages)."
                },
                "category": {
                    "type": "string",
                    "description": "A specific category for the dish (e.g., salad, pasta, cocktail, etc.)."
                },
                "ingredients": {
                    "type": "array",
                    "description": "List of ingredients without quantities, explicitly mentioned in the recipe. The ingredients may contain modifier related to cooking techniques. Do not infer ingredients. (e.g. grilled chicken, unsalted butter, granulated sugar, baking powder, salt, heavy cream, cocoa powder, almond extract, honey, olive oil, soy sauce, etc.)",
                    "items": {
                        "type": "string"
                    }
                },
                "alternative_ingredients": {
                    "type": ["array", "null"],
                    "description": "List of ingredients witout quantities, explicitly mentioned as alternatives in the recipe. Do not infer ingredients (e.g., gin, chives, almond, etc.). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "flavor_and_texture": {
                    "type": ["array", "null"],
                    "description": "Flavor profiles and textures mentioned or inferred (e.g., tangy, crispy). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "cooking_technique": {
                    "type": ["array", "null"],
                    "description": "Cooking methods explicitly mentioned (e.g., grilled, oven-roasted, simmered, charbroiled, sous vide, slow-cooked, air-fried, one-pot, etc). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "brand": {
                    "type": ["array", "null"],
                    "description": "Brand names explicitly mentioned. If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "preparation_level": {
                    "type": ["string", "null"],
                    "description": "The difficulty level of the recipe (e.g., Easy, Intermediate, Advanced). If none, set to null."
                },
                "total_time": {
                    "type": ["number", "null"],
                    "description": "Total time in minutes for preparation and cooking. If none, set to null."
                },
                "cultural_reference": {
                    "type": ["array", "null"],
                    "description": "Cuisine, cultural or regional associations (e.g., Italian, Indian, Chinese, Country, Southern, etc.). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "seasonality": {
                    "type": ["array", "null"],
                    "description": "Season or holiday associations (e.g., Winter, Thanksgiving). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                 "themes": {
                    "type": ["array", "null"],
                    "description": "Theme associations (e.g., party and gathering, comfort food, holiday meal, quick and easy recipe, kid-friendly, meal-prep and freezer friendly, etc. ). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "dietary_labels": {
                    "type": ["array", "null"],
                    "description": "Dietary accommodations explicitly mentioned (e.g., vegetarian, vegan, gluten-free, paleo, halal, kosher, etc ). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "health_labels": {
                    "type": ["array", "null"],
                    "description": "Health-related characteristics (e.g., low-calorie, high-protein, zero-sugar). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "sustainability_labels": {
                    "type": ["array", "null"],
                    "description": "Environmental and sourcing attributes (e.g., organic, grass-fed, cage-free, GMO-free, etc.). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "convenience_labels": {
                    "type": ["array", "null"],
                    "description": "Convenience labels (e.g., Quick, Meal Prep, One-pot, etc.). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "dish_name", "publication_date", "updated_date", "rating", "ratings_count",
                "reviews_count", "times_shared", "course", "category", "ingredients",
                "alternative_ingredients", "flavor_and_texture", "cooking_technique",
                "brand", "preparation_level", "total_time", "cultural_reference", "seasonality", "themes",
                "dietary_labels", "health_labels", "sustainability_labels", "convenience_labels"
            ],
            "additionalProperties": False
        }
    }
}
