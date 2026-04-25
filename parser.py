import google.genai as genai
from google.genai import types
import os
import json
import logging
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
        if r.ocr_hints:
            hints.append(r.ocr_hints)
    return "\n".join(hints)

def parse_ticket(image_path, vendor=None):
    """
    Parses a ticket image using Gemini 1.5 Flash in JSON mode with vendor-specific knowledge.
    """
    logging.info(f"🔍 Sending ticket image to Gemini (Target Vendor: {vendor})")
    
    vendor_hints = get_vendor_knowledge()
    img = Image.open(image_path)
    
    vendor_instruction = f"\n    The user has indicated this ticket is from: {vendor}.\n" if vendor else ""
    
    prompt = f"""
    You are an expert in Mexican retail tickets and invoicing (CFDI). {vendor_instruction}
    
    CRITICAL INSTRUCTION:
    Prioritize the 'VENDOR-SPECIFIC KNOWLEDGE BASE' below. 
    Each vendor uses unique labels and formats for their IDs (e.g., TR, TC, Folio, Web ID). 
    Only use 'GENERAL INSTRUCTIONS' if the specific vendor is not found in the knowledge base.

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
    - For Walmart: TR maps to 'transaction_number', TC maps to 'web_id'.
    - If you see multiple dates, the 'date' should be the purchase date.
    - Total must be a number only.
    - If information is missing, use null.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[
                types.Part.from_text(text=prompt),
                img
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        data = json.loads(response.text)
        logging.info(f"✅ Gemini successfully parsed data: {data}")
        return data
    except Exception as e:
        logging.error(f"❌ Gemini scan failed or returned invalid JSON: {e}")
        return None
