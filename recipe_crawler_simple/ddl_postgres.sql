-- Table: recipe.dishes

-- DROP TABLE IF EXISTS recipe.dishes;

CREATE TABLE IF NOT EXISTS recipe.dishes
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
    cooking_technique character varying[] COLLATE pg_catalog."default",
    season character varying COLLATE pg_catalog."default",
    source character varying COLLATE pg_catalog."default",
    date_created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    date_updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    star_rating numeric(3,2),
    num_ratings integer DEFAULT 0,
    num_reviews integer DEFAULT 0,
    CONSTRAINT dishes_pkey PRIMARY KEY (dish_id),
    CONSTRAINT dishes_dish_id_fkey FOREIGN KEY (dish_id)
        REFERENCES recipe.recipe_urls (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS recipe.dishes
    OWNER to postgres;





-- Table: recipe.dish_ingredients

-- DROP TABLE IF EXISTS recipe.dish_ingredients;

CREATE TABLE IF NOT EXISTS recipe.dish_ingredients
(
    dish_id uuid NOT NULL,
    ingredient_id integer NOT NULL DEFAULT nextval('recipe.dish_ingredients_ingredient_id_seq'::regclass),
    quantity numeric(18,3),
    units character varying COLLATE pg_catalog."default",
    format character varying COLLATE pg_catalog."default",
    type character varying COLLATE pg_catalog."default",
    ingredient_role character varying COLLATE pg_catalog."default",
    flavor_role character varying COLLATE pg_catalog."default",
    alternative_ingredients character varying[] COLLATE pg_catalog."default",
    date_added timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    prep_method character varying(255) COLLATE pg_catalog."default",
    ingredient character varying(255) COLLATE pg_catalog."default",
    flavor_ingredient character varying(100) COLLATE pg_catalog."default",
    CONSTRAINT dish_ingredients_pkey PRIMARY KEY (dish_id, ingredient_id),
    CONSTRAINT dish_ingredients_dish_id_fkey FOREIGN KEY (dish_id)
        REFERENCES recipe.dishes (dish_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS recipe.dish_ingredients
    OWNER to postgres;



-- Table: recipe.dish_attributes

-- DROP TABLE IF EXISTS recipe.dish_attributes;

CREATE TABLE IF NOT EXISTS recipe.dish_attributes
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
    CONSTRAINT dish_attributes_pkey PRIMARY KEY (dish_id),
    CONSTRAINT dish_attributes_dish_id_fkey FOREIGN KEY (dish_id)
        REFERENCES recipe.dishes (dish_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS recipe.dish_attributes
    OWNER to postgres;