import json

# IRDAI Non-Payable Items List (hardcoded for reliability)
NON_PAYABLE_ITEMS = {
    "surgical gloves", "gloves", "hand gloves",
    "syringe", "syringes", "injection syringe",
    "bed sheet", "bedsheet", "linen", "bed linen",
    "thermometer", "digital thermometer",
    "registration fee", "admission fee", "registration charges",
    "attendant charges", "attendant fee", "attendant food",
    "food for attendant", "relative food",
    "toiletries", "tissue paper", "cotton",
    "face mask", "mask", "shoe cover",
    "visitor pass", "phone charges", "tv charges",
    "diet charges", "laundry charges"
}

def detect_overcharges(bill_data: dict, policy_data: dict) -> dict:
    """
    Detects overcharges in a hospital bill against policy terms.
    Args:
        bill_data: output from extract_bill()
        policy_data: dict with policy terms
    Returns:
        dict with flags and total recoverable amount
    """
    flags = []

    # --- CHECK 1: Room Rent Cap Violation ---
    sum_insured = policy_data.get("sum_insured", 500000)
    room_rent_cap = policy_data.get("room_rent_cap", sum_insured * 0.01)

    room_items = [
        item for item in bill_data.get("line_items", [])
        if item.get("category") == "room_charges"
        and "room rent" in item.get("description", "").lower()
    ]

    if room_items:
        daily_rent = max(item.get("unit_price", 0) for item in room_items)
        days = sum(item.get("quantity", 1) for item in room_items
                   if "room rent" in item.get("description", "").lower())

        if daily_rent > room_rent_cap:
            excess_per_day = daily_rent - room_rent_cap
            recoverable = excess_per_day * days
            flags.append({
                "type": "ROOM_RENT_CAP_VIOLATION",
                "severity": "HIGH",
                "description": f"Room rent ₹{daily_rent:,.0f}/day exceeds policy cap of ₹{room_rent_cap:,.0f}/day (1% of sum insured)",
                "recoverable_amount": recoverable,
                "days_affected": days,
                "irdai_citation": "IRDAI (Protection of Policyholders' Interests) Regulations, 2024 — Room rent sub-limit clause",
                "recommendation": f"Claim refund of ₹{excess_per_day:,.0f}/day × {days} days = ₹{recoverable:,.0f}"
            })

    # --- CHECK 2: Non-Medical Consumables ---
    consumable_flags = []
    for item in bill_data.get("line_items", []):
        description = item.get("description", "").lower()
        total = item.get("total", 0)

        for non_payable in NON_PAYABLE_ITEMS:
            if non_payable in description and total > 0:
                consumable_flags.append({
                    "item": item.get("description"),
                    "amount": total
                })
                break

    if consumable_flags:
        total_consumables = sum(f["amount"] for f in consumable_flags)
        item_list = ", ".join(f["item"] for f in consumable_flags)
        flags.append({
            "type": "NON_MEDICAL_CONSUMABLES",
            "severity": "MEDIUM",
            "description": f"Non-medical consumables billed: {item_list}",
            "recoverable_amount": total_consumables,
            "items": consumable_flags,
            "irdai_citation": "IRDAI Master Circular on Standardisation of Exclusions — Non-Medical Expenses List",
            "recommendation": "Request removal or re-categorization of these items from the bill"
        })

    # --- CHECK 3: Admin Charges ---
    admin_flags = []
    admin_non_payable = {"registration fee", "admission fee", "attendant charges", "attendant fee"}

    for item in bill_data.get("line_items", []):
        description = item.get("description", "").lower()
        total = item.get("total", 0)
        for admin_item in admin_non_payable:
            if admin_item in description and total > 0:
                admin_flags.append({
                    "item": item.get("description"),
                    "amount": total
                })
                break

    if admin_flags:
        total_admin = sum(f["amount"] for f in admin_flags)
        item_list = ", ".join(f["item"] for f in admin_flags)
        flags.append({
            "type": "NON_PAYABLE_ADMIN_CHARGES",
            "severity": "MEDIUM",
            "description": f"Non-payable administrative charges: {item_list}",
            "recoverable_amount": total_admin,
            "items": admin_flags,
            "irdai_citation": "IRDAI Non-Medical Expenses List — Administrative charges not covered",
            "recommendation": "Dispute these charges with insurer as per IRDAI guidelines"
        })

    total_recoverable = sum(f["recoverable_amount"] for f in flags)

    return {
        "flags": flags,
        "total_recoverable": total_recoverable,
        "total_bill": bill_data.get("total_amount", 0),
        "recovery_percentage": round((total_recoverable / bill_data.get("total_amount", 1)) * 100, 1)
    }


if __name__ == "__main__":
    # Test with sample data
    sample_bill = {
        "patient_name": "Rajesh Kumar",
        "hospital_name": "Apollo Hospitals",
        "total_amount": 132800,
        "line_items": [
            {"description": "Room Rent @ Rs.8000/day", "quantity": 4, "unit_price": 8000, "total": 32000, "category": "room_charges"},
            {"description": "Nursing Charges", "quantity": 1, "unit_price": 8000, "total": 8000, "category": "room_charges"},
            {"description": "Appendectomy Surgery", "quantity": 1, "unit_price": 45000, "total": 45000, "category": "procedure"},
            {"description": "Surgical Gloves (10 pairs)", "quantity": 10, "unit_price": 150, "total": 1500, "category": "consumable"},
            {"description": "Syringes (20 units)", "quantity": 20, "unit_price": 40, "total": 800, "category": "consumable"},
            {"description": "Bed Sheet/Linen", "quantity": 1, "unit_price": 1200, "total": 1200, "category": "consumable"},
            {"description": "Thermometer", "quantity": 1, "unit_price": 500, "total": 500, "category": "consumable"},
            {"description": "Registration Fee", "quantity": 1, "unit_price": 1000, "total": 1000, "category": "admin"},
            {"description": "Attendant Charges", "quantity": 1, "unit_price": 2000, "total": 2000, "category": "admin"},
        ]
    }

    sample_policy = {
        "sum_insured": 500000,
        "room_rent_cap": 5000,
        "insurer": "HDFC Ergo"
    }

    result = detect_overcharges(sample_bill, sample_policy)
    print(json.dumps(result, indent=2))

    