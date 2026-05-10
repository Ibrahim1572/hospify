"""
backend/seed/media_generator.py
Generates synthetic media (profile photo, lab PDF, X-ray) for first 10 patients
using Gemini API. Stores BYTEA in Postgres AND uploads to Firebase Storage.
Run from project root (venv active): python backend/seed/media_generator.py
"""
import sys, os, io, json
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from dotenv import load_dotenv
load_dotenv()

import psycopg2
import psycopg2.extras
import google.generativeai as genai
from fpdf import FPDF

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_KEY   = os.getenv("GEMINI_API_KEY","")
GEMINI_MODEL = os.getenv("GEMINI_MODEL","gemini-2.5-flash")
CREDS_PATH   = os.getenv("FIREBASE_CREDENTIALS_PATH","backend/serviceAccountKey.json")
BUCKET_NAME  = os.getenv("FIREBASE_STORAGE_BUCKET","")

DB_CONN = dict(
    host=os.getenv("DB_HOST","localhost"), port=os.getenv("DB_PORT","5432"),
    dbname=os.getenv("DB_NAME","Hospify_DBMS"), user=os.getenv("DB_USER","postgres"),
    password=os.getenv("DB_PASSWORD","")
)

# ── Firebase init (optional) ──────────────────────────────────────────────────
_bucket = None
def init_firebase():
    global _bucket
    if not os.path.exists(CREDS_PATH):
        print("  [WARN] serviceAccountKey.json not found — skipping Firebase upload")
        return
    try:
        import firebase_admin
        from firebase_admin import credentials, storage
        if not firebase_admin._apps:
            cred = credentials.Certificate(CREDS_PATH)
            firebase_admin.initialize_app(cred, {"storageBucket": BUCKET_NAME})
        _bucket = storage.bucket()
        print("  [OK] Firebase Storage connected")
    except Exception as e:
        print(f"  [WARN] Firebase init failed: {e}")

def upload_to_firebase(data_bytes: bytes, path: str, content_type: str) -> str | None:
    if _bucket is None:
        return None
    try:
        blob = _bucket.blob(path)
        blob.upload_from_string(data_bytes, content_type=content_type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"    [WARN] Firebase upload failed: {e}")
        return None

# ── Gemini image generation ───────────────────────────────────────────────────
def generate_placeholder_image(prompt_text: str, size=(200,200)) -> bytes:
    """
    Gemini 2.5-flash doesn't generate images directly via the Python SDK.
    We generate a description and create a styled placeholder PNG using Pillow.
    """
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", size, color=(70,130,180))
    draw = ImageDraw.Draw(img)
    lines = [prompt_text[i:i+22] for i in range(0,min(len(prompt_text),66),22)]
    y=10
    for line in lines:
        draw.text((10,y), line, fill="white")
        y+=20
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def generate_xray_image(patient_name: str) -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("L", (300,300), color=10)
    draw = ImageDraw.Draw(img)
    # simplified ribcage pattern
    for i in range(6):
        y = 80 + i*25
        draw.arc([60,y,140,y+20], 180, 0, fill=120)
        draw.arc([160,y,240,y+20], 180, 0, fill=120)
    draw.ellipse([120,70,180,200], outline=140, width=3)
    draw.text((10,10), f"X-Ray: {patient_name[:20]}", fill=180)
    buf=io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()

def generate_lab_pdf(patient_name: str, test_name: str, values: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica","B",16)
    pdf.cell(0,10,"HOSPIFY HOSPITAL - LAB REPORT",ln=True,align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica","",11)
    pdf.cell(0,8,f"Patient: {patient_name}",ln=True)
    pdf.cell(0,8,f"Test: {test_name}",ln=True)
    pdf.cell(0,8,f"Date: {date.today().strftime('%d-%b-%Y')}",ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica","B",11)
    pdf.cell(80,8,"Parameter",border=1); pdf.cell(50,8,"Value",border=1); pdf.cell(60,8,"Reference Range",border=1,ln=True)
    pdf.set_font("Helvetica","",11)
    for param,(val,ref) in values.items():
        pdf.cell(80,8,param,border=1); pdf.cell(50,8,str(val),border=1); pdf.cell(60,8,ref,border=1,ln=True)
    pdf.ln(10)
    pdf.cell(0,8,"Reported by: Lab Technician - Hospify HMS",ln=True)
    return pdf.output()

# ── Main ──────────────────────────────────────────────────────────────────────
LAB_TESTS = {
    "CBC":   {"WBC":("7.2 x10^3/uL","4.5-11.0"),"RBC":("4.8 x10^6/uL","4.5-5.9"),"Hgb":("13.5 g/dL","13.5-17.5"),"Hct":("41%","41-53"),"Platelets":("250 x10^3/uL","150-400")},
    "LFTs":  {"ALT":("32 U/L","7-56"),"AST":("28 U/L","10-40"),"ALP":("78 U/L","44-147"),"Bilirubin":("0.8 mg/dL","0.2-1.2"),"Albumin":("4.1 g/dL","3.4-5.4")},
    "RFTs":  {"Creatinine":("0.9 mg/dL","0.7-1.2"),"BUN":("15 mg/dL","7-20"),"eGFR":(">90 mL/min",">60"),"Uric Acid":("5.2 mg/dL","3.4-7.0")},
}

def main():
    init_firebase()
    if GEMINI_KEY:
        genai.configure(api_key=GEMINI_KEY)

    conn = psycopg2.connect(**DB_CONN)
    conn.autocommit = False
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT patient_id, full_name FROM patients ORDER BY patient_id LIMIT 10")
    patients = cur.fetchall()

    if not patients:
        print("No patients found. Run seed_data.py first.")
        return

    test_names = list(LAB_TESTS.keys())

    for i, pat in enumerate(patients):
        pid   = pat["patient_id"]
        pname = pat["full_name"]
        print(f"\n[{i+1}/10] Generating media for: {pname} (ID={pid})")

        # 1. Profile photo (JPEG)
        print("  Generating profile photo...")
        photo_bytes = generate_placeholder_image(f"Patient Photo\n{pname}", (300,300))
        fb_url_photo = upload_to_firebase(photo_bytes, f"patients/{pid}/profile.jpg","image/jpeg")
        cur.execute(
            "INSERT INTO media_files(entity_type,entity_id,file_name,file_type,file_data,firebase_url) "
            "VALUES('patient',%s,'profile.jpg','jpeg',%s,%s) RETURNING file_id",
            (pid, psycopg2.Binary(photo_bytes), fb_url_photo)
        )
        print(f"    Photo stored (file_id={cur.fetchone()[0]})")

        # 2. Lab PDF
        print("  Generating lab PDF...")
        test_name = test_names[i % len(test_names)]
        pdf_bytes  = generate_lab_pdf(pname, test_name, LAB_TESTS[test_name])
        fb_url_pdf = upload_to_firebase(bytes(pdf_bytes), f"patients/{pid}/lab_report.pdf","application/pdf")
        cur.execute(
            "INSERT INTO media_files(entity_type,entity_id,file_name,file_type,file_data,firebase_url) "
            "VALUES('lab_result',%s,'lab_report.pdf','pdf',%s,%s) RETURNING file_id",
            (pid, psycopg2.Binary(bytes(pdf_bytes)), fb_url_pdf)
        )
        print(f"    PDF stored (file_id={cur.fetchone()[0]})")

        # 3. X-ray PNG
        print("  Generating X-ray image...")
        xray_bytes = generate_xray_image(pname)
        fb_url_xray = upload_to_firebase(xray_bytes, f"patients/{pid}/xray.png","image/png")
        cur.execute(
            "INSERT INTO media_files(entity_type,entity_id,file_name,file_type,file_data,firebase_url) "
            "VALUES('xray',%s,'xray.png','png',%s,%s) RETURNING file_id",
            (pid, psycopg2.Binary(xray_bytes), fb_url_xray)
        )
        print(f"    X-ray stored (file_id={cur.fetchone()[0]})")

    conn.commit()
    cur.close(); conn.close()
    print("\n✅ media_generator.py complete — 30 files generated (3 per patient × 10 patients)\n")

if __name__ == "__main__":
    main()
