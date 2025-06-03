-- -- Drop tables in correct order (foreign key dependencies)
-- DROP TABLE IF EXISTS dish_attributes;
-- DROP TABLE IF EXISTS dish_ingredients;
-- DROP TABLE IF EXISTS dishes;

-- Recreate dishes table without constraints
CREATE TABLE dishes(
  dish_id UUID,
  dish_name VARCHAR NOT NULL,
  description VARCHAR,
  dish_base_type VARCHAR,
  meal_time VARCHAR,
  food_format VARCHAR,
  general_category VARCHAR,
  specific_category VARCHAR,
  cuisine VARCHAR,
  country VARCHAR,
  complexity VARCHAR,
  serving_temperature VARCHAR,
  cooking_technique VARCHAR[],
  season VARCHAR,
  source VARCHAR,
  date_created TIMESTAMP DEFAULT(CURRENT_TIMESTAMP),
  date_updated TIMESTAMP DEFAULT(CURRENT_TIMESTAMP),
  star_rating DECIMAL(3,2),
  num_ratings INTEGER DEFAULT(0),
  num_reviews INTEGER DEFAULT(0)
);

-- Recreate dish_ingredients table without constraints
CREATE TABLE dish_ingredients(
  dish_id UUID,
  ingredient_id INTEGER,
  "name" VARCHAR NOT NULL,
  full_ingredient VARCHAR,
  quantity DECIMAL(18,3),
  units VARCHAR,
  format VARCHAR,
  "type" VARCHAR,
  ingredient_role VARCHAR,
  cooking_technique VARCHAR,
  flavor_role VARCHAR,
  alternatives VARCHAR[],
  flavor_notes VARCHAR[],
  date_added TIMESTAMP DEFAULT(CURRENT_TIMESTAMP)
);

-- Recreate dish_attributes table without constraints
CREATE TABLE dish_attributes(
  dish_id UUID,
  flavor_attributes VARCHAR[],
  texture_attributes VARCHAR[],
  aroma_attributes VARCHAR[],
  diet_preferences VARCHAR[],
  functional_health VARCHAR[],
  occasions VARCHAR[],
  convenience_attributes VARCHAR[],
  social_setting VARCHAR[],
  emotional_attributes VARCHAR[]
);