import os
import json
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.extract_bill import extract_bill
from tools.detect_overcharges import detect_overcharges
from tools.draft_email import draft_dispute_email

def run_claimkaro(
    bill_image_path: str,
    policy_data: dict
) -> dict:
    """
    Main ClaimKaro agent pipeline.
    Step 1: Extract bill data
    Step 2: Detect overcharges
    Step 3: Draft dispute email
    """
    print("\n🔍 Step 1: Extracting bill data...")
    bill_data = extract_bill(bill_image_path)
    print(f"✅ Extracted {len(bill_data.get('line_items', []))} line items")
    print(f"   Patient: {bill_data.get('patient_name')}")
    print(f"   Hospital: {bill_data.get('hospital_name')}")
    print(f"   Total Bill: ₹{bill_data.get('total_amount', 0):,.0f}")

    print("\n⚠️  Step 2: Detecting overcharges...")
    overcharge_result = detect_overcharges(bill_data, policy_data)
    print(f"✅ Found {len(overcharge_result['flags'])} violations")
    print(f"   Total Recoverable: ₹{overcharge_result['total_recoverable']:,.0f}")
    print(f"   Recovery %: {overcharge_result['recovery_percentage']}%")

    dispute_email = None
    if overcharge_result["total_recoverable"] > 0:
        print("\n📧 Step 3: Drafting dispute email...")
        dispute_email = draft_dispute_email(
            patient_name=bill_data.get("patient_name", "Patient"),
            policy_number=policy_data.get("policy_number", "N/A"),
            insurer_name=policy_data.get("insurer", "Insurance Company"),
            hospital_name=bill_data.get("hospital_name", "Hospital"),
            flags=overcharge_result["flags"],
            total_recoverable=overcharge_result["total_recoverable"]
        )
        print("✅ Dispute email drafted")

    return {
        "bill_data": bill_data,
        "overcharge_result": overcharge_result,
        "dispute_email": dispute_email,
        "summary": {
            "patient": bill_data.get("patient_name"),
            "hospital": bill_data.get("hospital_name"),
            "total_bill": bill_data.get("total_amount", 0),
            "total_recoverable": overcharge_result["total_recoverable"],
            "recovery_percentage": overcharge_result["recovery_percentage"],
            "violations_found": len(overcharge_result["flags"])
        }
    }


if __name__ == "__main__":
    sample_policy = {
        "policy_number": "HDFC-2023-456789",
        "insurer": "HDFC Ergo Health Insurance",
        "sum_insured": 500000,
        "room_rent_cap": 5000
    }

    result = run_claimkaro("../sample_bill.png", sample_policy)

    print("\n" + "="*50)
    print("CLAIMKARO ANALYSIS COMPLETE")
    print("="*50)
    print(json.dumps(result["summary"], indent=2))
    print("\n--- DISPUTE EMAIL ---")
    print(result["dispute_email"])


