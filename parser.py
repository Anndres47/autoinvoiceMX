import google.generativeai as genai
import os
import json
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def parse_ticket(image_path):
    """
    Parses a ticket image using Gemini 1.5 Flash and returns a JSON object.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    img = Image.open(image_path)
    
    prompt = """
    Analyze this Mexican retail ticket and extract the following information in JSON format:
    - vendor (e.g., OXXO, Walmart, Amazon)
    - folio (Ticket number or ID)
    - total (Total amount as a number)
    - date (Date of purchase)
    - rfc (Vendor RFC if visible)

    If the image is ineligible or information is missing, return an empty JSON or specify the missing fields.
    Return ONLY the JSON object.
    """
    
    response = model.generate_content([prompt, img])
    
    try:
        # Clean up response if it contains markdown formatting
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
            
        data = json.loads(text)
        return data
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        return None
