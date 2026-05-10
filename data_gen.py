import os
import psycopg2
import google.generativeai as genai
import io
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Please set GEMINI_API_KEY in your .env file.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
# For text generation
text_model = genai.GenerativeModel('gemini-2.5-flash')

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "Hospify_DBMS"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )

def setup_table(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS generated_patient_media (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER REFERENCES patients(patient_id),
            media_type VARCHAR(50),
            content_text TEXT,
            image_data BYTEA,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()

def generate_medical_report(patient_name, age, gender):
    prompt = f"Generate a brief, realistic medical checkup report for a patient named {patient_name}, age {age}, gender {gender}. Include a generic diagnosis and recommendation. Do not use formatting, just plain text."
    try:
        response = text_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating text report: {e}")
        return f"Standard Medical Report for {patient_name}."

def generate_image_dummy(prompt):
    """
    Since the standard free Gemini API tier (gemini-2.5-flash) only outputs text and processes images (multimodal input), 
    direct image generation (Imagen) requires an enterprise GCP account or specific access.
    To ensure this script runs for you without crashing, we generate a synthetic image byte stream using a free placeholder service 
    that embeds the Gemini-inspired text prompt into the image itself.
    """
    # Create a simple placeholder image with text
    safe_text = prompt.replace(" ", "+")[:50]
    url = f"https://placehold.co/400x400/000000/FFFFFF/png?text={safe_text}"
    try:
        response = requests.get(url)
        return response.content
    except:
        return b""

def main():
    conn = get_db_connection()
    setup_table(conn)
    cur = conn.cursor()

    # Get first 10 patients
    cur.execute("SELECT patient_id, full_name, dob, gender FROM patients ORDER BY patient_id LIMIT 10")
    patients = cur.fetchall()

    if not patients:
        print("No patients found in the database.")
        return

    for pat in patients:
        patient_id, name, dob, gender = pat
        # Calculate approximate age
        age = 30 if not dob else (2026 - dob.year)
        
        print(f"\nProcessing patient: {name} (ID: {patient_id})")

        # 1. Generate Report
        print("  Generating medical report...")
        report_text = generate_medical_report(name, age, gender)
        cur.execute(
            "INSERT INTO generated_patient_media (patient_id, media_type, content_text) VALUES (%s, %s, %s)",
            (patient_id, 'medical_report', report_text)
        )

        # 2. Generate X-Ray (Simulated due to API limits on standard keys)
        print("  Generating X-Ray image...")
        xray_prompt = f"Chest X-Ray for {name}"
        xray_bytes = generate_image_dummy(xray_prompt)
        cur.execute(
            "INSERT INTO generated_patient_media (patient_id, media_type, image_data) VALUES (%s, %s, %s)",
            (patient_id, 'xray', psycopg2.Binary(xray_bytes))
        )

        # 3. Generate Profile Image (Simulated)
        print("  Generating Profile image...")
        profile_prompt = f"Profile photo of {name}"
        profile_bytes = generate_image_dummy(profile_prompt)
        cur.execute(
            "INSERT INTO generated_patient_media (patient_id, media_type, image_data) VALUES (%s, %s, %s)",
            (patient_id, 'profile_image', psycopg2.Binary(profile_bytes))
        )

        conn.commit()

    cur.close()
    conn.close()
    print("\n✅ Data generation complete! Data stored in 'generated_patient_media' table.")

if __name__ == "__main__":
    main()
