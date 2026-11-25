import os
import sys
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.extract_bill import extract_bill
from tools.detect_overcharges import detect_overcharges
from tools.draft_email import draft_dispute_email

app = FastAPI(title="ClaimKaro API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
SAMPLE_BILL = os.path.join(BASE_DIR, "sample_bill.png")


def run_pipeline(bill_path: str, policy_number: str, insurer_name: str,
                 sum_insured: float, room_rent_cap: float) -> dict:
    bill_data = extract_bill(bill_path)

    policy_data = {
        "policy_number": policy_number,
        "insurer": insurer_name,
        "sum_insured": sum_insured,
        "room_rent_cap": room_rent_cap
    }

    overcharge_result = detect_overcharges(bill_data, policy_data)

    dispute_email = None
    if overcharge_result["total_recoverable"] > 0:
        dispute_email = draft_dispute_email(
            patient_name=bill_data.get("patient_name", "Patient"),
            policy_number=policy_number,
            insurer_name=insurer_name,
            hospital_name=bill_data.get("hospital_name", "Hospital"),
            flags=overcharge_result["flags"],
            total_recoverable=overcharge_result["total_recoverable"]
        )

    return {
        "success": True,
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


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ClaimKaro API"}


@app.post("/analyze")
async def analyze_bill(
    bill_file: UploadFile = File(...),
    sum_insured: float = Form(default=500000),
    room_rent_cap: float = Form(default=5000),
    policy_number: str = Form(default="N/A"),
    insurer_name: str = Form(default="Insurance Company")
):
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if bill_file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: JPG, PNG, PDF")

    ext = bill_file.filename.split(".")[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        content = await bill_file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        print(f"Analyzing uploaded bill: {bill_file.filename}")
        return run_pipeline(tmp_path, policy_number, insurer_name, sum_insured, room_rent_cap)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/analyze-demo")
async def analyze_demo(
    sum_insured: float = Form(default=500000),
    room_rent_cap: float = Form(default=5000),
    policy_number: str = Form(default="HDFC-2023-456789"),
    insurer_name: str = Form(default="HDFC Ergo Health Insurance")
):
    if not os.path.exists(SAMPLE_BILL):
        raise HTTPException(status_code=404, detail="Demo bill not found on server")

    try:
        print("Running demo analysis on sample bill...")
        return run_pipeline(SAMPLE_BILL, policy_number, insurer_name, sum_insured, room_rent_cap)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve frontend — must be last
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
async def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"service": "ClaimKaro", "status": "API running, frontend not found"}

    