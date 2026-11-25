import os
import json
import base64
import subprocess
import time
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

def extract_bill(image_path: str) -> dict:
    """
    Extracts structured data from a hospital bill image.
    Args:
        image_path: local path to bill image (jpg/png/pdf)
    Returns:
        dict with patient info and line items
    """
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    ext = image_path.lower().split(".")[-1]
    mime_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "pdf": "application/pdf"
    }
    mime_type = mime_map.get(ext, "image/jpeg")

    payload = {
        "contents": [{
            "parts": [
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_data
                    }
                },
                {
                    "text": """Extract ALL information from this Indian hospital bill.
Return ONLY valid JSON with this exact structure:
{
  "patient_name": "string",
  "hospital_name": "string",
  "admission_date": "string",
  "discharge_date": "string",
  "total_amount": 0,
  "line_items": [
    {
      "description": "string",
      "quantity": 1,
      "unit_price": 0,
      "total": 0,
      "category": "room_charges|procedure|medicine|consumable|diagnostic|admin|other"
    }
  ],
  "insurance_info": null,
  "notes": null
}
If a field is not found use null. For numbers use 0 if not found."""
                }
            ]
        }],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }

    for attempt in range(5):
        result = subprocess.run([
            "curl", "-s", "-X", "POST",
            f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload)
        ], capture_output=True, text=True, timeout=120)

        if not result.stdout.strip():
            print(f"   Empty response, retrying in 10s... (attempt {attempt+1}/5)")
            time.sleep(10)
            continue

        response = json.loads(result.stdout)

        if "error" in response:
            code = response["error"].get("code", 0)
            message = response["error"].get("message", "Unknown error")
            if code == 503:
                print(f"   Model busy, retrying in 15s... (attempt {attempt+1}/5)")
                time.sleep(15)
                continue
            else:
                raise Exception(f"API error: {message}")

        text = response["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)

    raise Exception("Failed after 5 attempts — model unavailable. Try again in a few minutes.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = extract_bill(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python extract_bill.py <path_to_bill_image>")