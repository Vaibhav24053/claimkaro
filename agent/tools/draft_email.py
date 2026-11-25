import os
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

def call_gemini(prompt: str) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3}
    }
    result = subprocess.run([
        "curl", "-s", "-X", "POST",
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload)
    ], capture_output=True, text=True, timeout=120)

    response = json.loads(result.stdout)
    if "error" in response:
        raise Exception(f"API error: {response['error']['message']}")
    return response["candidates"][0]["content"]["parts"][0]["text"]


def draft_dispute_email(
    patient_name: str,
    policy_number: str,
    insurer_name: str,
    hospital_name: str,
    flags: list,
    total_recoverable: float
) -> str:
    flags_text = "\n".join([
        f"- {f['type']}: {f['description']} (₹{f['recoverable_amount']:,.0f} recoverable)\n  Citation: {f['irdai_citation']}"
        for f in flags
    ])

    prompt = f"""Draft a formal insurance claim dispute email for an Indian patient.

DETAILS:
- Patient: {patient_name}
- Policy Number: {policy_number}
- Insurer: {insurer_name}
- Hospital: {hospital_name}
- Total Disputed Amount: ₹{total_recoverable:,.0f}

VIOLATIONS FOUND:
{flags_text}

REQUIREMENTS:
- Formal, firm but professional tone
- Cite specific IRDAI regulations mentioned above
- Reference the policy number
- Demand written response within 15 days (as per IRDAI Regulation 13)
- Mention escalation to Insurance Ombudsman if unresolved within 15 days
- Include subject line
- Sign as "{patient_name} (Policyholder)"

Write the complete email now:"""

    return call_gemini(prompt)


if __name__ == "__main__":
    sample_flags = [
        {
            "type": "ROOM_RENT_CAP_VIOLATION",
            "description": "Room rent ₹8,000/day exceeds policy cap of ₹5,000/day",
            "recoverable_amount": 12000,
            "irdai_citation": "IRDAI (Protection of Policyholders Interests) Regulations, 2024"
        },
        {
            "type": "NON_MEDICAL_CONSUMABLES",
            "description": "Surgical gloves, syringes, bed sheet billed as medical items",
            "recoverable_amount": 4000,
            "irdai_citation": "IRDAI Master Circular on Standardisation of Exclusions"
        }
    ]

    email = draft_dispute_email(
        patient_name="Rajesh Kumar",
        policy_number="HDFC-2023-456789",
        insurer_name="HDFC Ergo Health Insurance",
        hospital_name="Apollo Hospitals Mumbai",
        flags=sample_flags,
        total_recoverable=16000
    )
    print(email)
    