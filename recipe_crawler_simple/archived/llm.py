import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from prompts import RESPONSE_FORMAT_RECIPE_EXTRACTION, SYSTEM_PROMPT_RECIPE_EXTRACTION
import json

def check_recipe_url_with_openai(url, client):
    """Use OpenAI API to check if a URL is a recipe URL."""
    try:
        logging.info(f"Checking recipe URL with OpenAI: {url}")
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1,
            temperature=0,
            messages=[
                {"role": "system", "content": """You are an expert recipe URL identifier. 
                                                Your task is to identify whether the given URL is a recipe or not. 
                                                Please respond with a single letter y for yes and n for no."""},
                {"role": "user", "content": url}
            ]
        )
        response = completion.choices[0].message.content.lower()
        logging.info(f"OpenAI response for {url}: {response}")
        return response == 'y'
    except Exception as e:
        logging.error(f"Error calling OpenAI API for {url}: {e}")
        return False
    

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=4, max=10))
def extract_recipe_data(text, client):
    """Extract recipe data using OpenAI."""
    try:
        logging.info("Extracting recipe data using OpenAI")
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_RECIPE_EXTRACTION},
                {"role": "user", "content": text}
            ],
            response_format=RESPONSE_FORMAT_RECIPE_EXTRACTION
        )
        response = completion.choices[0].message.content
        logging.debug("OpenAI extraction response received")
        return json.loads(response) if response else {}
    except Exception as e:
        logging.error(f"OpenAI extraction error: {e}")
        return {}