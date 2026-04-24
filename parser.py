import google.genai as genai
from google.genai import types
import os
import json
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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

def parse_ticket(image_path, vendor=None):
    """
    Parses a ticket image using Gemini 1.5 Flash in JSON mode with vendor-specific knowledge.
    """
    vendor_hints = get_vendor_knowledge()
    
    img = Image.open(image_path)
    
    vendor_instruction = f"\n    The user has indicated this ticket is from: {vendor}.\n" if vendor else ""
    
    prompt = f"""
    You are an expert in Mexican retail tickets and invoicing (CFDI). {vendor_instruction}
    Extract data from this image into this JSON schema:
    {{
        "vendor": "string (e.g., OXXO, Walmart, Amazon)",
        "folio": "string",
        "total": number,
        "date": "string (YYYY-MM-DD)",
        "rfc": "string",
        "extra_data": {{
            "web_id": "string or null",
            "transaction_number": "string or null",
            "store_id": "string or null",
            "payment_method": "string (e.g., Efectivo, Tarjeta, 28, 04) or null"
        }}

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
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[img, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error in Gemini JSON parsing: {e}")
        return None