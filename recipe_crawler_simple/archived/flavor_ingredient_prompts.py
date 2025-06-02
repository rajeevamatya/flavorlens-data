

SYSTEM_PROMPT_RECIPE_EXTRACTION = """
You are an expert in recipe data extraction. Your task is to parse recipes and extract 
structured data according to the provided JSON schema. If the input contains more than one recipe, 
only extract data for the first recipe. If the document contains no recipe, outpull empty json object. 

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
                "star_rating": {
                    "type": ["number", "null"],
                    "description": "The recipe’s rating as a numerical value from 1-5 (e.g., 4, 4.5, etc.). If none, set to null."
                },
                "ratings_count": {
                    "type": ["number", "null"],
                    "description": "The total number of ratings for the recipe. If none, set to null."
                },
                "course": {
                    "type": "string",
                    "description": "The course of the meal (e.g., starters, mains, desserts, beverages)."
                },
                "category": {
                    "type": "string",
                    "description": "A specific category for the dish (e.g., salad, pasta, burger, cocktail, etc.)."
                },
                "country_of_origin": {
                    "type": ["array", "null"],
                    "description": "Country of origin of the dishes (e.g., Italy, India, China, Thailand, America, etc.) If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "ingredients": {
                    "type": "array",
                    "description": """List of ingredients without quantities or modifiers.  The ingredients must be explicitly 
                    mentioned in the recipe. Do not infer anything. (e.g. chicken, butter, white sugar, baking powder, 
                    salt, heavy cream, cocoa powder, almond extract, honey, olive oil, soy sauce, etc.)""",
                    "items": {
                        "type": "string"
                    }
                },
                "alternative_ingredients": {
                    "type": ["array", "null"],
                    "description": """List of ingredients without quantities or modifiers, that areexplicitly mentioned as 
                    alternatives in the recipe. Do not infer ingredients (e.g., gin, chives, almond, etc.). If none, set to null.""",
                    "items": {
                        "type": "string"
                    }
                },
                "primary_flavors": {
                    "type": ["array", "null"],
                    "description": "Primary flavor profiles explicitly mentioned or clearly inferred (e.g., tangy, sweet, savory, vanilla). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "secondary_flavors": {
                    "type": ["array", "null"],
                    "description": "Scondary flavor profiles explicitly mentioned or clearly inferred (e.g., tangy, sweet, savory, vanilla). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "mouthfeel": {
                    "type": ["array", "null"],
                    "description": "Mouthfeel attributes explicitly mentioned or clearly inferred (e.g., creamy, smooth, gritty, refreshing). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "aroma": {
                    "type": ["array", "null"],
                    "description": "Aroma explicitly mentioned or clearly inferred (e.g., vanilla, citrusy, floral). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "cooking_methods": {
                    "type": ["array", "null"],
                    "description": "Cooking methods explicitly mentioned (e.g., grilled, oven-roasted, simmered, charbroiled, sous vide, slow-cooked, air-fried, one-pot, etc). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "flavor_development_methods": {
                    "type": ["array", "null"],
                    "description": "Flavor development methods explicitly mentioned (e.g., caramelization, Maillard reaction, fermentation, aging, infusion, etc). If none, set to null.",
                    "items": {
                        "type": "string"
                    }
                },
                "seasonality": {
                    "type": ["array", "null"],
                    "description": "Season association for the dish (e.g., Winter, Summer, Spring, Autumn). If none, set to null.",
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
                "sensory_analysis": {
                    "type": "object",
                    "description": "Sensory analysis of flavor attributes, rated on a scale from 0 to 5.",
                    "properties": {
                        "sweetness": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 5,
                            "description": "Sweetness level of the dish."
                        },
                        "saltiness": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 5,
                            "description": "Saltiness level of the dish."
                        },
                        "bitterness": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 5,
                            "description": "Bitterness level of the dish."
                        },
                        "sourness": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 5,
                            "description": "Sourness level of the dish."
                        },
                        "umami": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 5,
                            "description": "Umami (savory) level of the dish."
                        },
                        "richness": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 5,
                            "description": "Richness (fullness) level of the dish."
                        },
                        "complexity": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 5,
                            "description": "Complexity of flavors in the dish."
                        }
                    }
                },
            },
            "required": [
                "dish_name", 
                "publication_date", "updated_date", "star_rating", "ratings_count",
                "course", "category", "country_of_origin",
                "ingredients", "alternative_ingredients", "primary_flavors", "secondary_flavors",
                "mouthfeel", "cooking_methods", "flavor_development_methods",
                "seasonality","dietary_labels",
                "sensory_analysis",
            ],
            "additionalProperties": False
        }
    }
}
