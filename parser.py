import google.generativeai as genai
import os
import json
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

from vendors.oxxo import OxxoRecipe
from vendors.walmart import WalmartRecipe

def get_vendor_knowledge():
    """Aggregates hints from all supported vendors."""
    hints = []
    recipes = [OxxoRecipe, WalmartRecipe]
    for r in recipes:
        # Instantiate temporarily to get hints or use a static property
        # For simplicity, we'll just pull the property from a fresh instance
        try:
            instance = r(headless=True)
            hints.append(instance.ocr_hints)
            instance.close()
        except:
            pass
    return "\n".join(hints)

def parse_ticket(image_path):
    """
    Parses a ticket image using Gemini 1.5 Flash in JSON mode with vendor-specific knowledge.
    """
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    
    vendor_hints = get_vendor_knowledge()
    
    img = Image.open(image_path)
    
    prompt = f"""
    You are an expert in Mexican retail tickets and invoicing (CFDI). 
    Extract data from this image into this JSON schema:
    {{
        "vendor": "string (e.g., OXXO, Walmart, Amazon)",
        "folio": "string",
        "total": number,
        "date": "string (YYYY-MM-DD)",
        "rfc": "string",
        "extra_data": {
            "web_id": "string or null",
            "transaction_number": "string or null",
            "store_id": "string or null",
            "payment_method": "string (e.g., Efectivo, Tarjeta, 28, 04) or null"
        }

    }}

    VENDOR-SPECIFIC KNOWLEDGE BASE:
    {vendor_hints}

    GENERAL INSTRUCTIONS:
    - Look for 'Folio', 'Web ID', 'No. Transacción', 'Ticket ID'.
    - If you see multiple dates, the 'date' should be the purchase date.
    - Total must be a number only.
    - If information is missing, use null.
    """
    
    try:
        response = model.generate_content([prompt, img])
        return json.loads(response.text)
    except Exception as e:
        print(f"Error in Gemini JSON parsing: {e}")
        return None
