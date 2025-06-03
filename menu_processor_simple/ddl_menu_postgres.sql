
-- Table: menu.dishes (Based on recipe.dishes structure)
-- DROP TABLE IF EXISTS menu.dishes;


CREATE TABLE IF NOT EXISTS menu.dishes
(
    dish_id uuid NOT NULL,
    dish_name character varying COLLATE pg_catalog."default" NOT NULL,
    description character varying COLLATE pg_catalog."default",
    meal_time character varying COLLATE pg_catalog."default",
    general_category character varying COLLATE pg_catalog."default",
    specific_category character varying COLLATE pg_catalog."default",
    cuisine character varying COLLATE pg_catalog."default",
    complexity character varying COLLATE pg_catalog."default",
    serving_temperature character varying COLLATE pg_catalog."default",
    season character varying COLLATE pg_catalog."default",
    source character varying COLLATE pg_catalog."default",
    date_created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    date_modified timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    star_rating numeric(3,2),
    num_ratings integer DEFAULT 0,
    num_reviews integer DEFAULT 0,
    date_published date,
    date_updated date,
    CONSTRAINT dishes_pkey PRIMARY KEY (dish_id),
    CONSTRAINT dishes_dish_id_fkey FOREIGN KEY (dish_id)
        REFERENCES menu.menu_items (item_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS menu.dishes
    OWNER to postgres;

-- Table: menu.dish_ingredients (Based on recipe.dish_ingredients structure)
-- DROP TABLE IF EXISTS menu.dish_ingredients;

CREATE TABLE IF NOT EXISTS menu.dish_ingredients
(
    dish_id uuid NOT NULL,
    ingredient_id SERIAL NOT NULL,
    quantity numeric(18,3),
    units character varying COLLATE pg_catalog."default",
    format character varying COLLATE pg_catalog."default",
    type character varying COLLATE pg_catalog."default",
    ingredient_role character varying COLLATE pg_catalog."default",
    flavor_role character varying COLLATE pg_catalog."default",
    alternative_ingredients character varying[] COLLATE pg_catalog."default",
    date_added timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    prep_method character varying COLLATE pg_catalog."default",
    ingredient character varying COLLATE pg_catalog."default",
    flavor_ingredient character varying COLLATE pg_catalog."default",
    CONSTRAINT dish_ingredients_pkey PRIMARY KEY (dish_id, ingredient_id),
    CONSTRAINT dish_ingredients_dish_id_fkey FOREIGN KEY (dish_id)
        REFERENCES menu.dishes (dish_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS menu.dish_ingredients
    OWNER to postgres;

-- Table: menu.dish_attributes (Based on recipe.dish_attributes structure)
-- DROP TABLE IF EXISTS menu.dish_attributes;

CREATE TABLE IF NOT EXISTS menu.dish_attributes
(
    dish_id uuid NOT NULL,
    flavor_attributes character varying[] COLLATE pg_catalog."default",
    texture_attributes character varying[] COLLATE pg_catalog."default",
    aroma_attributes character varying[] COLLATE pg_catalog."default",
    diet_preferences character varying[] COLLATE pg_catalog."default",
    functional_health character varying[] COLLATE pg_catalog."default",
    occasions character varying[] COLLATE pg_catalog."default",
    convenience_attributes character varying[] COLLATE pg_catalog."default",
    social_setting character varying[] COLLATE pg_catalog."default",
    emotional_attributes character varying[] COLLATE pg_catalog."default",
    cooking_techniques character varying[] COLLATE pg_catalog."default",
    CONSTRAINT dish_attributes_pkey PRIMARY KEY (dish_id),
    CONSTRAINT dish_attributes_dish_id_fkey FOREIGN KEY (dish_id)
        REFERENCES menu.dishes (dish_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS menu.dish_attributes
    OWNER to postgres;