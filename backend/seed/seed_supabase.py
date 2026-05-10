"""
backend/seed/seed_supabase.py
Comprehensive seed script for Hospify HMS on Supabase.
Run from project root: python backend/seed/seed_supabase.py
"""
import sys, os, random
from pathlib import Path
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load env from Vercel share location
env_path = Path("/vercel/share/.env.project")
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
else:
    from dotenv import load_dotenv
    load_dotenv()

import psycopg2
from werkzeug.security import generate_password_hash

# ── Connection ────────────────────────────────────────────────────────────────
def connect():
    url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    if url:
        p = urlparse(url)
        return psycopg2.connect(
            host=p.hostname, port=p.port or 5432,
            dbname=p.path.lstrip("/"),
            user=p.username, password=p.password,
            sslmode="require"
        )
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "Hospify_DBMS"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )

# ── Helpers ───────────────────────────────────────────────────────────────────
def rand_dt(days_ago_min=1, days_ago_max=180):
    return datetime.now() - timedelta(
        days=random.randint(days_ago_min, days_ago_max),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )

def rand_future(days_min=1, days_max=30):
    return datetime.now() + timedelta(
        days=random.randint(days_min, days_max),
        hours=random.randint(8, 16)
    )

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    conn = connect()
    conn.autocommit = False
    cur = conn.cursor()

    print("Clearing existing data (in FK-safe order)...")
    cur.execute("SET session_replication_role = 'replica'")
    for tbl in [
        "audit_log", "alerts", "payments", "bill_items", "bills",
        "lab_results", "lab_orders", "prescription_items", "prescriptions",
        "vitals", "admissions", "appointments",
        "medicine_inventory", "medicines",
        "pharmacists", "lab_technicians", "nurses", "doctors",
        "beds", "wards", "patients", "users",
    ]:
        cur.execute(f"DELETE FROM {tbl}")
    cur.execute("SET session_replication_role = 'origin'")
    conn.commit()
    print("  Done.")

    # ──────────────────────────────────────────────────────────────────────────
    # 1. USERS  (30 total)
    # ──────────────────────────────────────────────────────────────────────────
    print("Seeding users...")
    pw = generate_password_hash("Password123!")

    user_defs = [
        # (full_name, email, role)
        ("Admin Khan",           "admin@hospify.com",          "super_admin"),
        ("Sara Ahmed",           "receptionist@hospify.com",   "receptionist"),
        ("Usman Tariq",          "receptionist2@hospify.com",  "receptionist"),
        ("Billing Zara",         "billing.zara@hospify.com",   "billing_staff"),
        ("Billing Hamid",        "billing.hamid@hospify.com",  "billing_staff"),
        # Doctors (10)
        ("Dr. Khalid Mir",       "dr.khalid@hospify.com",      "doctor"),
        ("Dr. Ayesha Raza",      "dr.ayesha@hospify.com",      "doctor"),
        ("Dr. Omar Farooq",      "dr.omar@hospify.com",        "doctor"),
        ("Dr. Nadia Hussain",    "dr.nadia@hospify.com",       "doctor"),
        ("Dr. Bilal Sheikh",     "dr.bilal@hospify.com",       "doctor"),
        ("Dr. Saima Javed",      "dr.saima@hospify.com",       "doctor"),
        ("Dr. Faisal Qureshi",   "dr.faisal@hospify.com",      "doctor"),
        ("Dr. Hina Malik",       "dr.hina@hospify.com",        "doctor"),
        ("Dr. Tariq Mahmood",    "dr.tariq@hospify.com",       "doctor"),
        ("Dr. Amna Siddiqui",    "dr.amna@hospify.com",        "doctor"),
        # Nurses (8)
        ("Nurse Fatima Bibi",    "nurse.fatima@hospify.com",   "nurse"),
        ("Nurse Bilal Khan",     "nurse.bilal@hospify.com",    "nurse"),
        ("Nurse Asma Rani",      "nurse.asma@hospify.com",     "nurse"),
        ("Nurse Zeeshan Ali",    "nurse.zeeshan@hospify.com",  "nurse"),
        ("Nurse Huma Bano",      "nurse.huma@hospify.com",     "nurse"),
        ("Nurse Imran Shah",     "nurse.imran@hospify.com",    "nurse"),
        ("Nurse Rabia Noor",     "nurse.rabia@hospify.com",    "nurse"),
        ("Nurse Kamran Butt",    "nurse.kamran@hospify.com",   "nurse"),
        # Lab Techs (4)
        ("Tech Raza Shah",       "lab.raza@hospify.com",       "lab_technician"),
        ("Tech Sobia Farhan",    "lab.sobia@hospify.com",      "lab_technician"),
        ("Tech Adeel Awan",      "lab.adeel@hospify.com",      "lab_technician"),
        ("Tech Mariam Nisar",    "lab.mariam@hospify.com",     "lab_technician"),
        # Pharmacists (3)
        ("Pharma Nadia Aziz",    "pharma.nadia@hospify.com",   "pharmacist"),
        ("Pharma Sohail Khan",   "pharma.sohail@hospify.com",  "pharmacist"),
        ("Pharma Lubna Waqar",   "pharma.lubna@hospify.com",   "pharmacist"),
    ]

    uid = {}
    for name, email, role in user_defs:
        cur.execute(
            "INSERT INTO users(full_name, email, password_hash, role) "
            "VALUES(%s,%s,%s,%s) RETURNING user_id",
            (name, email, pw, role)
        )
        uid[email] = cur.fetchone()[0]
    conn.commit()
    print(f"  {len(uid)} users inserted.")

    # ──────────────────────────────────────────────────────────────────────────
    # 2. WARDS (7)
    # ──────────────────────────────────────────────────────────────────────────
    print("Seeding wards...")
    wards_def = [
        ("General Ward A",    "general",    1, 20),
        ("General Ward B",    "general",    1, 20),
        ("ICU",               "icu",        2, 10),
        ("Pediatric Ward",    "pediatric",  3, 15),
        ("Maternity Ward",    "maternity",  3, 12),
        ("Surgical Ward",     "surgical",   2, 18),
        ("Orthopedic Ward",   "orthopedic", 4, 14),
    ]
    ward_ids = []
    for wname, wtype, floor, beds in wards_def:
        cur.execute(
            "INSERT INTO wards(ward_name, ward_type, floor_number, total_beds) "
            "VALUES(%s,%s,%s,%s) RETURNING ward_id",
            (wname, wtype, floor, beds)
        )
        ward_ids.append((cur.fetchone()[0], beds))
    conn.commit()

    # 3. BEDS per ward
    print("Seeding beds...")
    bed_ids_by_ward = {}
    all_bed_ids = []
    bed_types = ["general", "general", "general", "semi-private", "private"]
    for ward_id, total in ward_ids:
        bed_ids_by_ward[ward_id] = []
        for i in range(1, total + 1):
            btype = random.choice(bed_types)
            cur.execute(
                "INSERT INTO beds(ward_id, bed_number, bed_type, status) "
                "VALUES(%s,%s,%s,'available') RETURNING bed_id",
                (ward_id, f"W{ward_id}-{i:02d}", btype)
            )
            bid = cur.fetchone()[0]
            bed_ids_by_ward[ward_id].append(bid)
            all_bed_ids.append(bid)
    conn.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. STAFF ROLES
    # ──────────────────────────────────────────────────────────────────────────
    print("Seeding doctors, nurses, techs, pharmacists...")
    doctor_defs = [
        ("dr.khalid@hospify.com",  "Cardiology",       "MBBS, FCPS",   "Mon,Tue,Wed,Thu",    "0300-1234001"),
        ("dr.ayesha@hospify.com",  "Pediatrics",       "MBBS, MCPS",   "Tue,Wed,Thu,Fri",    "0300-1234002"),
        ("dr.omar@hospify.com",    "General Surgery",  "MBBS, FRCS",   "Mon,Wed,Fri",        "0300-1234003"),
        ("dr.nadia@hospify.com",   "Gynecology",       "MBBS, FCPS",   "Mon,Tue,Thu,Sat",    "0300-1234004"),
        ("dr.bilal@hospify.com",   "Orthopedics",      "MBBS, FCPS",   "Tue,Thu,Sat",        "0300-1234005"),
        ("dr.saima@hospify.com",   "Neurology",        "MBBS, MRCP",   "Mon,Wed,Fri",        "0300-1234006"),
        ("dr.faisal@hospify.com",  "Nephrology",       "MBBS, FCPS",   "Mon,Tue,Wed",        "0300-1234007"),
        ("dr.hina@hospify.com",    "Dermatology",      "MBBS, DDVL",   "Wed,Thu,Fri",        "0300-1234008"),
        ("dr.tariq@hospify.com",   "Pulmonology",      "MBBS, MRCP",   "Mon,Tue,Thu",        "0300-1234009"),
        ("dr.amna@hospify.com",    "Gastroenterology", "MBBS, FCPS",   "Tue,Wed,Fri,Sat",    "0300-1234010"),
    ]
    doc_ids = []
    doc_email_to_id = {}
    for email, spec, qual, days, phone in doctor_defs:
        cur.execute(
            "INSERT INTO doctors(user_id, specialization, qualification, available_days, phone) "
            "VALUES(%s,%s,%s,%s,%s) RETURNING doctor_id",
            (uid[email], spec, qual, days, phone)
        )
        did = cur.fetchone()[0]
        doc_ids.append(did)
        doc_email_to_id[email] = did

    nurse_emails = [
        "nurse.fatima@hospify.com", "nurse.bilal@hospify.com",
        "nurse.asma@hospify.com",   "nurse.zeeshan@hospify.com",
        "nurse.huma@hospify.com",   "nurse.imran@hospify.com",
        "nurse.rabia@hospify.com",  "nurse.kamran@hospify.com",
    ]
    shifts = ["morning", "evening", "night"]
    nurse_ids = []
    flat_ward_ids = [w[0] for w in ward_ids]
    for i, email in enumerate(nurse_emails):
        cur.execute(
            "INSERT INTO nurses(user_id, ward_id, shift) VALUES(%s,%s,%s) RETURNING nurse_id",
            (uid[email], flat_ward_ids[i % len(flat_ward_ids)], shifts[i % 3])
        )
        nurse_ids.append(cur.fetchone()[0])

    tech_emails = ["lab.raza@hospify.com","lab.sobia@hospify.com","lab.adeel@hospify.com","lab.mariam@hospify.com"]
    tech_ids = []
    for email in tech_emails:
        cur.execute("INSERT INTO lab_technicians(user_id) VALUES(%s) RETURNING tech_id", (uid[email],))
        tech_ids.append(cur.fetchone()[0])

    pharma_emails = ["pharma.nadia@hospify.com","pharma.sohail@hospify.com","pharma.lubna@hospify.com"]
    for email in pharma_emails:
        cur.execute("INSERT INTO pharmacists(user_id) VALUES(%s)", (uid[email],))

    conn.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. PATIENTS (60)
    # ──────────────────────────────────────────────────────────────────────────
    print("Seeding patients (60)...")
    patient_pool = [
        ("Muhammad Ali",        date(1985,  3, 15), "male",   "3520112345671", "0300-1234567", "12 Gulberg, Lahore",       "A+",  "Ali Sr — 0300-9876543"),
        ("Fatima Khan",         date(1992,  7, 22), "female", "3520198765432", "0311-1234567", "5 Clifton, Karachi",        "B+",  "Khan Sr — 0311-1111111"),
        ("Ahmed Raza",          date(1970, 11,  5), "male",   "3520287654321", "0321-1234567", "33 F-7, Islamabad",         "O+",  "Raza Mo — 0321-2345678"),
        ("Zainab Malik",        date(2005,  2, 10), "female", "3520376543210", "0331-1234567", "7 Hayatabad, Peshawar",     "AB+", "Malik — 0331-2345678"),
        ("Hassan Siddiqui",     date(1958,  9, 30), "male",   "3520465432109", "0341-1234567", "2 Jinnah Rd, Quetta",       "A-",  "Siddiqui — 0341-2345678"),
        ("Amna Butt",           date(1999,  4, 18), "female", "3520554321098", "0351-1234567", "15 Peoples Colony, Faisalabad","B-","Butt — 0351-2345678"),
        ("Usman Tariq",         date(1945, 12,  1), "male",   "3520643210987", "0361-1234567", "Bosan Rd, Multan",          "O-",  "Tariq — 0361-2345678"),
        ("Sana Iqbal",          date(2010,  6, 25), "female", "3520732109876", "0371-1234567", "Saddar, Rawalpindi",        "AB-", "Iqbal — 0371-2345678"),
        ("Bilal Chaudhry",      date(1988,  8, 14), "male",   "3520821098765", "0381-1234567", "Sialkot Cantt",             "A+",  "Chaudhry — 0381-2345678"),
        ("Maryam Sher",         date(1975,  1,  3), "female", "3520910987654", "0391-1234567", "GT Rd, Gujranwala",         "B+",  "Sher — 0391-2345678"),
        ("Imran Shah",          date(1982,  5, 20), "male",   "3610112345671", "0300-2234567", "3 Model Town, Lahore",      "O+",  "Shah — 0300-3334567"),
        ("Nadia Aziz",          date(1990, 12,  8), "female", "3610198765432", "0311-2234567", "DHA Phase 5, Karachi",      "A+",  "Aziz — 0311-3334567"),
        ("Tariq Mahmood",       date(1965,  3, 28), "male",   "3610287654321", "0321-2234567", "G-10, Islamabad",           "B-",  "Mahmood — 0321-3334567"),
        ("Lubna Waqar",         date(2001,  9, 14), "female", "3610376543210", "0331-2234567", "Dalazak Rd, Peshawar",      "AB+", "Waqar — 0331-3334567"),
        ("Saad Rehman",         date(1993,  7,  7), "male",   "3610465432109", "0341-2234567", "Quetta Cantt",              "O-",  "Rehman — 0341-3334567"),
        ("Hina Baig",           date(1978,  4, 22), "female", "3610554321098", "0351-2234567", "Peoples Colony 2, Faisalabad","A+","Baig — 0351-3334567"),
        ("Kamran Ali",          date(1955, 11, 30), "male",   "3610643210987", "0361-2234567", "Cantt, Multan",             "B+",  "Ali — 0361-3334567"),
        ("Rabia Noor",          date(2008,  2, 17), "female", "3610732109876", "0371-2234567", "Chaklala, Rawalpindi",      "O+",  "Noor — 0371-3334567"),
        ("Faisal Qureshi",      date(1986,  6,  3), "male",   "3610821098765", "0381-2234567", "Sialkot City",              "A-",  "Qureshi — 0381-3334567"),
        ("Asma Rani",           date(1971,  8, 11), "female", "3610910987654", "0391-2234567", "Gujranwala City",           "AB-", "Rani — 0391-3334567"),
        ("Shahid Nawaz",        date(1980, 10, 19), "male",   "3710112345671", "0300-3234567", "Johar Town, Lahore",        "B+",  "Nawaz — 0300-4334567"),
        ("Sobia Farhan",        date(1996,  3, 24), "female", "3710198765432", "0311-3234567", "Gulshan-e-Iqbal, Karachi",  "O+",  "Farhan — 0311-4334567"),
        ("Adeel Awan",          date(1968,  1, 15), "male",   "3710287654321", "0321-3234567", "I-8, Islamabad",            "A+",  "Awan — 0321-4334567"),
        ("Mariam Nisar",        date(2003, 11, 28), "female", "3710376543210", "0331-3234567", "Ring Rd, Peshawar",         "B-",  "Nisar — 0331-4334567"),
        ("Zahid Hussain",       date(1950,  6, 10), "male",   "3710465432109", "0341-3234567", "Sariab Rd, Quetta",         "AB+", "Hussain — 0341-4334567"),
        ("Sonia Mirza",         date(1987,  9, 19), "female", "3710554321098", "0351-3234567", "Millat Town, Faisalabad",   "O-",  "Mirza — 0351-4334567"),
        ("Arslan Butt",         date(1976,  4,  5), "male",   "3710643210987", "0361-3234567", "Old Shujabad Rd, Multan",   "A+",  "Butt — 0361-4334567"),
        ("Farzana Khatoon",     date(2012,  7, 21), "female", "3710732109876", "0371-3234567", "Westridge, Rawalpindi",     "B+",  "Khatoon — 0371-4334567"),
        ("Waqas Aslam",         date(1991,  2,  9), "male",   "3710821098765", "0381-3234567", "Kashmir Rd, Sialkot",       "O+",  "Aslam — 0381-4334567"),
        ("Rukhsana Parveen",    date(1963, 12, 31), "female", "3710910987654", "0391-3234567", "Trust Colony, Gujranwala",  "A-",  "Parveen — 0391-4334567"),
        ("Junaid Akhtar",       date(1984,  5, 16), "male",   "3810112345671", "0300-4234567", "Bahria Town, Lahore",       "AB+", "Akhtar — 0300-5334567"),
        ("Mehwish Hayat",       date(1997,  8, 27), "female", "3810198765432", "0311-4234567", "Nazimabad, Karachi",        "B-",  "Hayat — 0311-5334567"),
        ("Naeem Baig",          date(1972, 10,  4), "male",   "3810287654321", "0321-4234567", "E-11, Islamabad",           "O-",  "Baig — 0321-5334567"),
        ("Samina Nawaz",        date(2006,  4, 12), "female", "3810376543210", "0331-4234567", "Arbab Rd, Peshawar",        "A+",  "Nawaz — 0331-5334567"),
        ("Azhar Iqbal",         date(1961,  7, 23), "male",   "3810465432109", "0341-4234567", "Brewery Rd, Quetta",        "B+",  "Iqbal — 0341-5334567"),
        ("Ghazala Bibi",        date(1989, 11, 30), "female", "3810554321098", "0351-4234567", "Samanabad, Faisalabad",     "O+",  "Bibi — 0351-5334567"),
        ("Shahzad Mehmood",     date(1974,  3,  8), "male",   "3810643210987", "0361-4234567", "Gulgasht Colony, Multan",   "AB-", "Mehmood — 0361-5334567"),
        ("Nasreen Sultana",     date(2009,  1, 17), "female", "3810732109876", "0371-4234567", "Dhok Syedan, Rawalpindi",   "A-",  "Sultana — 0371-5334567"),
        ("Rizwan Anwar",        date(1983,  9, 26), "male",   "3810821098765", "0381-4234567", "Sambrial, Sialkot",         "B-",  "Anwar — 0381-5334567"),
        ("Shazia Parveen",      date(1966,  6, 14), "female", "3810910987654", "0391-4234567", "Satellite Town, Gujranwala","O-",  "Parveen — 0391-5334567"),
        ("Usman Shafiq",        date(1979,  2, 22), "male",   "3910112345671", "0300-5234567", "Valencia Town, Lahore",     "A+",  "Shafiq — 0300-6334567"),
        ("Farah Naz",           date(1994, 12,  3), "female", "3910198765432", "0311-5234567", "Korangi, Karachi",          "AB+", "Naz — 0311-6334567"),
        ("Pervaiz Ahmad",       date(1957,  8, 19), "male",   "3910287654321", "0321-5234567", "F-6, Islamabad",            "B+",  "Ahmad — 0321-6334567"),
        ("Nida Butt",           date(2004,  5, 30), "female", "3910376543210", "0331-5234567", "University Rd, Peshawar",   "O+",  "Butt — 0331-6334567"),
        ("Musharraf Khan",      date(1948, 11, 11), "male",   "3910465432109", "0341-5234567", "Airport Rd, Quetta",        "A-",  "Khan — 0341-6334567"),
        ("Razia Sultana",       date(1981,  7,  6), "female", "3910554321098", "0351-5234567", "Gulberg, Faisalabad",       "B-",  "Sultana — 0351-6334567"),
        ("Mansoor Ahmed",       date(1967,  4, 25), "male",   "3910643210987", "0361-5234567", "Shah Rukn-e-Alam, Multan",  "AB+", "Ahmed — 0361-6334567"),
        ("Uzma Khalid",         date(2011,  9,  8), "female", "3910732109876", "0371-5234567", "Raja Bazaar, Rawalpindi",   "O-",  "Khalid — 0371-6334567"),
        ("Sohaib Zahid",        date(1995,  3, 17), "male",   "3910821098765", "0381-5234567", "Cantt, Sialkot",            "A+",  "Zahid — 0381-6334567"),
        ("Bushra Arshad",       date(1960,  1, 29), "female", "3910910987654", "0391-5234567", "Model Town, Gujranwala",    "B+",  "Arshad — 0391-6334567"),
        ("Farhan Altaf",        date(1988, 10, 13), "male",   "4010112345671", "0300-6234567", "Cavalry Ground, Lahore",    "O+",  "Altaf — 0300-7334567"),
        ("Tahira Siddiqui",     date(1973,  6,  2), "female", "4010198765432", "0311-6234567", "PECHS, Karachi",            "AB-", "Siddiqui — 0311-7334567"),
        ("Irfan Cheema",        date(1962,  4, 18), "male",   "4010287654321", "0321-6234567", "H-13, Islamabad",           "A-",  "Cheema — 0321-7334567"),
        ("Anjum Zaheer",        date(2007, 12, 25), "female", "4010376543210", "0331-6234567", "Peshawar Cantt",            "B+",  "Zaheer — 0331-7334567"),
        ("Khalil Ahmad",        date(1952,  8,  7), "male",   "4010465432109", "0341-6234567", "Mastung Rd, Quetta",        "O+",  "Ahmad — 0341-7334567"),
        ("Shabana Malik",       date(1977,  5, 15), "female", "4010554321098", "0351-6234567", "D-Ground, Faisalabad",      "A+",  "Malik — 0351-7334567"),
        ("Javed Iqbal",         date(1969,  2, 28), "male",   "4010643210987", "0361-6234567", "Hussain Agahi, Multan",     "B-",  "Iqbal — 0361-7334567"),
        ("Zubeda Khatoon",      date(2013,  7, 10), "female", "4010732109876", "0371-6234567", "Morgah, Rawalpindi",        "AB+", "Khatoon — 0371-7334567"),
        ("Naveed Anwar",        date(1986, 11, 22), "male",   "4010821098765", "0381-6234567", "Daska, Sialkot",            "O-",  "Anwar — 0381-7334567"),
        ("Sajida Kausar",       date(1955,  3, 31), "female", "4010910987654", "0391-6234567", "Kamoke Rd, Gujranwala",     "A+",  "Kausar — 0391-7334567"),
    ]

    pat_ids = []
    for p in patient_pool:
        cur.execute(
            "INSERT INTO patients(full_name,dob,gender,cnic,phone,address,blood_group,emergency_contact) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING patient_id", p
        )
        pat_ids.append(cur.fetchone()[0])
    conn.commit()
    print(f"  {len(pat_ids)} patients inserted.")

    # ──────────────────────────────────────────────────────────────────────────
    # 6. MEDICINES (50) + INVENTORY
    # ──────────────────────────────────────────────────────────────────────────
    print("Seeding medicines (50) + inventory...")
    med_list = [
        ("Paracetamol","Panadol","Analgesic","tablet"),
        ("Amoxicillin","Amoxil","Antibiotic","capsule"),
        ("Metformin","Glucophage","Antidiabetic","tablet"),
        ("Amlodipine","Norvasc","Antihypertensive","tablet"),
        ("Omeprazole","Losec","PPI","capsule"),
        ("Atorvastatin","Lipitor","Statin","tablet"),
        ("Ibuprofen","Brufen","NSAID","tablet"),
        ("Ciprofloxacin","Cipro","Antibiotic","tablet"),
        ("Losartan","Cozaar","ARB","tablet"),
        ("Pantoprazole","Protonix","PPI","tablet"),
        ("Salbutamol","Ventolin","Bronchodilator","inhaler"),
        ("Metronidazole","Flagyl","Antibiotic","tablet"),
        ("Dexamethasone","Decadron","Steroid","injection"),
        ("Furosemide","Lasix","Diuretic","tablet"),
        ("Warfarin","Coumadin","Anticoagulant","tablet"),
        ("Ceftriaxone","Rocephin","Antibiotic","injection"),
        ("Morphine","MS Contin","Opioid","injection"),
        ("Insulin Glargine","Lantus","Insulin","injection"),
        ("Aspirin","Ecotrin","Antiplatelet","tablet"),
        ("Ranitidine","Zantac","H2 Blocker","tablet"),
        ("Lisinopril","Prinivil","ACE Inhibitor","tablet"),
        ("Enalapril","Vasotec","ACE Inhibitor","tablet"),
        ("Hydrochlorothiazide","Microzide","Diuretic","tablet"),
        ("Simvastatin","Zocor","Statin","tablet"),
        ("Clopidogrel","Plavix","Antiplatelet","tablet"),
        ("Ramipril","Altace","ACE Inhibitor","tablet"),
        ("Bisoprolol","Zebeta","Beta Blocker","tablet"),
        ("Carvedilol","Coreg","Beta Blocker","tablet"),
        ("Diltiazem","Cardizem","CCB","tablet"),
        ("Verapamil","Calan","CCB","tablet"),
        ("Spironolactone","Aldactone","Diuretic","tablet"),
        ("Digoxin","Lanoxin","Cardiac Glycoside","tablet"),
        ("Heparin","Heparin","Anticoagulant","injection"),
        ("Enoxaparin","Clexane","Anticoagulant","injection"),
        ("Ondansetron","Zofran","Antiemetic","tablet"),
        ("Domperidone","Motilium","Antiemetic","tablet"),
        ("Loperamide","Imodium","Antidiarrheal","capsule"),
        ("Cetirizine","Zyrtec","Antihistamine","tablet"),
        ("Loratadine","Claritin","Antihistamine","tablet"),
        ("Montelukast","Singulair","Leukotriene Antagonist","tablet"),
        ("Fluticasone","Flixotide","Corticosteroid","inhaler"),
        ("Tiotropium","Spiriva","Anticholinergic","inhaler"),
        ("Amitriptyline","Elavil","Antidepressant","tablet"),
        ("Sertraline","Zoloft","SSRI","tablet"),
        ("Diazepam","Valium","Benzodiazepine","tablet"),
        ("Phenytoin","Dilantin","Anticonvulsant","tablet"),
        ("Levetiracetam","Keppra","Anticonvulsant","tablet"),
        ("Tramadol","Ultram","Analgesic","capsule"),
        ("Ketorolac","Toradol","NSAID","injection"),
        ("Prednisolone","Prelone","Steroid","tablet"),
    ]
    med_ids = []
    for g, b, cat, unit in med_list:
        cur.execute(
            "INSERT INTO medicines(generic_name,brand_name,category,unit) "
            "VALUES(%s,%s,%s,%s) RETURNING medicine_id", (g, b, cat, unit)
        )
        mid = cur.fetchone()[0]
        med_ids.append(mid)
        qty = random.randint(8, 400)
        reorder = random.randint(10, 30)
        cur.execute(
            "INSERT INTO medicine_inventory(medicine_id,quantity_available,reorder_level) "
            "VALUES(%s,%s,%s)", (mid, qty, reorder)
        )
    conn.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 7. APPOINTMENTS (80)
    # ──────────────────────────────────────────────────────────────────────────
    print("Seeding appointments (80)...")
    appt_statuses = ["scheduled","scheduled","completed","completed","completed","cancelled","no_show"]
    reasons = [
        "Routine checkup", "Follow-up visit", "Fever and fatigue",
        "Chest pain evaluation", "Hypertension review", "Diabetes management",
        "Post-operative care", "Knee pain consultation", "Skin rash evaluation",
        "Breathing difficulty", "Abdominal pain", "Headache workup",
        "Back pain", "Kidney function review", "Asthma follow-up",
    ]
    for i in range(80):
        pid = random.choice(pat_ids)
        did = random.choice(doc_ids)
        status = random.choice(appt_statuses)
        if status == "scheduled":
            sched = rand_future(1, 20)
        else:
            sched = rand_dt(1, 120)
        cur.execute(
            "INSERT INTO appointments(patient_id,doctor_id,scheduled_at,status,reason) "
            "VALUES(%s,%s,%s,%s,%s)",
            (pid, did, sched, status, random.choice(reasons))
        )
    conn.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 8. ADMISSIONS (50)
    # ──────────────────────────────────────────────────────────────────────────
    print("Seeding admissions (50)...")
    cur.execute("SET session_replication_role = 'replica'")

    adm_types = ["general","emergency","elective","observation"]
    adm_ids = []

    # 25 active admissions — assign unique beds
    random.shuffle(all_bed_ids)
    active_beds = all_bed_ids[:25]
    used_patients_active = set()

    for i in range(25):
        # avoid duplicate patient in active admissions
        pid = random.choice(pat_ids)
        for _ in range(20):
            if pid not in used_patients_active:
                break
            pid = random.choice(pat_ids)
        used_patients_active.add(pid)

        did = random.choice(doc_ids)
        bid = active_beds[i]
        admit_dt = rand_dt(1, 30)
        cur.execute(
            "INSERT INTO admissions(patient_id,bed_id,doctor_id,admission_type,status,admitted_at,notes) "
            "VALUES(%s,%s,%s,%s,'active',%s,%s) RETURNING admission_id",
            (pid, bid, did, random.choice(adm_types), admit_dt,
             f"Patient admitted with {random.choice(reasons)}. Stable condition.")
        )
        row = cur.fetchone()
        if row:
            adm_ids.append(row[0])
            cur.execute("UPDATE beds SET status='occupied' WHERE bed_id=%s", (bid,))

    # 25 discharged admissions
    for i in range(25):
        pid = random.choice(pat_ids)
        did = random.choice(doc_ids)
        bid = all_bed_ids[25 + i] if 25 + i < len(all_bed_ids) else random.choice(all_bed_ids)
        admit_dt = rand_dt(10, 180)
        dis_dt = admit_dt + timedelta(days=random.randint(2, 14))
        cur.execute(
            "INSERT INTO admissions(patient_id,bed_id,doctor_id,admission_type,status,admitted_at,discharged_at,notes) "
            "VALUES(%s,%s,%s,%s,'discharged',%s,%s,%s) RETURNING admission_id",
            (pid, bid, did, random.choice(adm_types), admit_dt, dis_dt,
             f"Patient discharged in stable condition. Follow-up in {random.randint(1,4)} weeks.")
        )
        row = cur.fetchone()
        if row:
            adm_ids.append(row[0])

    cur.execute("SET session_replication_role = 'origin'")
    conn.commit()
    print(f"  {len(adm_ids)} admissions inserted.")

    # ──────────────────────────────────────────────────────────────────────────
    # 9. VITALS (3-6 per active admission)
    # ──────────────────────────────────────────────────────────────────────────
    print("Seeding vitals...")
    vital_notes = [
        "Patient resting comfortably.", "Mild discomfort reported.",
        "Improving steadily.", "Vitals stable.", "Patient ambulatory.",
        "Requires close monitoring.", "Post-medication vitals normal.",
    ]
    for aid in adm_ids[:25]:  # active admissions
        count = random.randint(3, 6)
        for j in range(count):
            rec_dt = datetime.now() - timedelta(hours=j * random.randint(4, 8))
            cur.execute(
                "INSERT INTO vitals(admission_id,nurse_id,temperature,blood_pressure_sys,"
                "blood_pressure_dia,pulse,oxygen_saturation,weight,recorded_at,notes) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (aid, random.choice(nurse_ids),
                 round(random.uniform(36.2, 39.0), 1),
                 random.randint(105, 155),
                 random.randint(65, 95),
                 random.randint(58, 105),
                 round(random.uniform(92.0, 99.5), 1),
                 round(random.uniform(45.0, 100.0), 1),
                 rec_dt,
                 random.choice(vital_notes))
            )
    conn.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 10. PRESCRIPTIONS + ITEMS (60 prescriptions)
    # ──────────────────────────────────────────────────────────────────────────
    print("Seeding prescriptions (60)...")
    freq_options = ["Once daily","Twice daily","Three times daily","Every 8 hours","Every 6 hours","At night","As needed"]
    dosage_options = ["1 tab","2 tabs","1 cap","0.5 tab","5 ml","10 ml","1 injection","2 injections"]
    rx_notes = [
        "Take with food.", "Avoid alcohol.", "Monitor blood pressure.",
        "Review in 2 weeks.", "Take at bedtime.", "Continue until course complete.",
    ]
    rx_ids = []
    for i in range(60):
        aid = random.choice(adm_ids)
        did = random.choice(doc_ids)
        rx_dt = rand_dt(1, 90)
        cur.execute(
            "INSERT INTO prescriptions(admission_id,doctor_id,prescribed_at,notes) "
            "VALUES(%s,%s,%s,%s) RETURNING prescription_id",
            (aid, did, rx_dt, random.choice(rx_notes))
        )
        rx_id = cur.fetchone()[0]
        rx_ids.append(rx_id)
        for _ in range(random.randint(1, 4)):
            mid = random.choice(med_ids)
            cur.execute(
                "INSERT INTO prescription_items(prescription_id,medicine_id,dosage,frequency,duration_days,instructions) "
                "VALUES(%s,%s,%s,%s,%s,%s)",
                (rx_id, mid,
                 random.choice(dosage_options),
                 random.choice(freq_options),
                 random.randint(3, 21),
                 random.choice(rx_notes))
            )
    conn.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 11. LAB ORDERS + RESULTS (70 orders)
    # ──────────────────────────────────────────────────────────────────────────
    print("Seeding lab orders + results (70)...")
    tests = [
        "CBC", "LFTs", "RFTs", "Blood Culture", "Urine RE/ME",
        "ECG", "Chest X-Ray", "Blood Sugar Fasting", "Blood Sugar Random",
        "Lipid Profile", "Thyroid Panel (TSH/T3/T4)", "HbA1c",
        "Serum Electrolytes", "Prothrombin Time", "Serum Creatinine",
        "Urine Culture & Sensitivity", "Echocardiogram", "Ultrasound Abdomen",
        "CT Scan Head", "MRI Spine",
    ]
    priorities = ["routine","routine","routine","urgent","stat"]
    result_summaries = [
        "All values within normal reference ranges.",
        "Mild leukocytosis noted — likely infectious cause. Clinical correlation advised.",
        "Elevated creatinine — suggest nephrology consult.",
        "Haemoglobin low at 9.2 g/dL — iron deficiency anaemia likely.",
        "TSH elevated (8.2 mIU/L) — primary hypothyroidism. Levothyroxine initiated.",
        "Blood glucose markedly elevated (380 mg/dL) — adjust insulin dose.",
        "LFTs mildly elevated — monitor and avoid hepatotoxic drugs.",
        "Chest X-Ray shows bilateral infiltrates — pneumonia suspected.",
        "ECG: Sinus tachycardia, no ST changes.",
        "Lipid profile: LDL elevated at 160 mg/dL — statin therapy recommended.",
        "Urine culture: E. coli isolated, sensitive to ciprofloxacin.",
        "CT Head: No acute intracranial pathology.",
        "Ultrasound abdomen: Mild hepatomegaly noted.",
        "Prothrombin time prolonged — adjust anticoagulant dose.",
        "HbA1c: 9.1% — suboptimal glycaemic control. Intensify diabetes regimen.",
    ]
    order_ids = []
    for i in range(70):
        aid = random.choice(adm_ids)
        did = random.choice(doc_ids)
        status = random.choice(["pending","in_progress","completed","completed","completed"])
        ord_dt = rand_dt(1, 60)
        cur.execute(
            "INSERT INTO lab_orders(admission_id,doctor_id,test_name,ordered_at,status,priority) "
            "VALUES(%s,%s,%s,%s,%s,%s) RETURNING order_id",
            (aid, did, random.choice(tests), ord_dt, status, random.choice(priorities))
        )
        oid = cur.fetchone()[0]
        order_ids.append((oid, status))

    conn.commit()

    # Results for completed orders
    for oid, status in order_ids:
        if status == "completed":
            res_dt = datetime.now() - timedelta(hours=random.randint(1, 48))
            cur.execute(
                "INSERT INTO lab_results(order_id,tech_id,result_summary,resulted_at,notes) "
                "VALUES(%s,%s,%s,%s,%s)",
                (oid, random.choice(tech_ids),
                 random.choice(result_summaries), res_dt,
                 random.choice(["No further action needed.", "Follow-up test in 1 week.", "Urgent clinical review advised.", ""]))
            )
    conn.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 12. BILLS + BILL_ITEMS + PAYMENTS (for discharged admissions)
    # ──────────────────────────────────────────────────────────────────────────
    print("Seeding bills + items + payments (25)...")
    billing_uid = uid["billing.zara@hospify.com"]
    billing_uid2 = uid["billing.hamid@hospify.com"]
    bill_statuses = ["paid","paid","paid","partial","pending"]

    service_types = [
        ("bed",          "Bed charges (per day)",         2000, 5),
        ("consultation", "Doctor consultation fee",       2500, 1),
        ("lab",          "Laboratory tests",              1500, 2),
        ("pharmacy",     "Medicines and pharmacy",        3000, 1),
        ("nursing",      "Nursing care charges",          1000, 3),
        ("procedure",    "Minor procedure fee",           5000, 1),
        ("imaging",      "Radiology / Imaging",           4500, 1),
        ("ot",           "Operation theatre charges",    15000, 1),
    ]

    for i, aid in enumerate(adm_ids[25:]):  # discharged admissions
        bstatus = random.choice(bill_statuses)
        gen_by = billing_uid if i % 2 == 0 else billing_uid2

        # Build items
        selected = random.sample(service_types, random.randint(2, 5))
        total = sum(s[2] * random.randint(1, s[3]) for s in selected)
        discount = random.choice([0, 0, 0, 500, 1000, 2000])
        net = max(0, total - discount)

        if bstatus == "paid":
            paid = net
        elif bstatus == "partial":
            paid = round(net * random.uniform(0.3, 0.7), 2)
        else:
            paid = 0

        cur.execute(
            "INSERT INTO bills(admission_id,generated_by,total_amount,discount,paid_amount,status) "
            "VALUES(%s,%s,%s,%s,%s,%s) RETURNING bill_id",
            (aid, gen_by, net, discount, paid, bstatus)
        )
        bid = cur.fetchone()[0]

        for stype, desc, unit_price, max_qty in selected:
            qty = random.randint(1, max_qty)
            cur.execute(
                "INSERT INTO bill_items(bill_id,service_type,description,quantity,unit_price) "
                "VALUES(%s,%s,%s,%s,%s)",
                (bid, stype, desc, qty, unit_price)
            )

        if paid > 0:
            method = random.choice(["cash","card","bank_transfer","insurance"])
            cur.execute(
                "INSERT INTO payments(bill_id,amount,payment_method,received_by) "
                "VALUES(%s,%s,%s,%s)",
                (bid, paid, method, gen_by)
            )
            # For partial bills, sometimes add a second payment
            if bstatus == "partial" and random.random() > 0.6:
                extra = round(paid * 0.2, 2)
                cur.execute(
                    "INSERT INTO payments(bill_id,amount,payment_method,received_by) "
                    "VALUES(%s,%s,%s,%s)",
                    (bid, extra, "cash", gen_by)
                )

    conn.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 13. ALERTS (15)
    # ──────────────────────────────────────────────────────────────────────────
    print("Seeding alerts (15)...")
    alert_defs = [
        ("low_inventory",    "Paracetamol stock is critically low (8 units remaining).",           False),
        ("low_inventory",    "Ceftriaxone injection nearly out of stock (5 units left).",          False),
        ("low_inventory",    "Insulin Glargine below reorder level — only 9 units available.",     True),
        ("bed_capacity",     "ICU at 90% capacity — only 1 bed available.",                        False),
        ("bed_capacity",     "Surgical Ward fully occupied. No beds available.",                    False),
        ("lab_overdue",      "Lab result for order #12 is overdue by 6 hours.",                    True),
        ("lab_overdue",      "STAT order pending for admission #5 — no result after 3 hours.",     False),
        ("billing_overdue",  "Bill for admission #18 has been unpaid for 10 days.",                True),
        ("billing_overdue",  "Pending payment reminder: 3 bills over 7 days old.",                 False),
        ("patient_critical", "Patient in ICU Bed W3-03 requires immediate physician review.",      False),
        ("vitals_abnormal",  "Oxygen saturation dropped below 90% — ICU patient alert.",           False),
        ("vitals_abnormal",  "High fever (39.8°C) recorded for patient in Pediatric Ward.",        True),
        ("scheduled_maintenance","Ward A scheduled for deep cleaning — 2 beds temporarily unavailable.", True),
        ("system",           "Backup completed successfully at 03:00 AM.",                         True),
        ("system",           "New user registered: dr.amna@hospify.com",                          True),
    ]
    for atype, msg, resolved in alert_defs:
        cur.execute(
            "INSERT INTO alerts(alert_type,message,is_resolved,entity_id) VALUES(%s,%s,%s,%s)",
            (atype, msg, resolved, random.randint(1, 10))
        )
    conn.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # DONE
    # ──────────────────────────────────────────────────────────────────────────
    cur.close()
    conn.close()

    print("\n" + "="*60)
    print("  Hospify HMS — Seed Complete!")
    print("="*60)
    print(f"  Users:        {len(user_defs)}")
    print(f"  Wards:        {len(ward_ids)}")
    print(f"  Beds:         {len(all_bed_ids)}")
    print(f"  Patients:     {len(pat_ids)}")
    print(f"  Medicines:    {len(med_ids)}")
    print(f"  Admissions:   {len(adm_ids)}")
    print(f"  Appointments: 80")
    print(f"  Prescriptions:{len(rx_ids)}")
    print(f"  Lab Orders:   70")
    print(f"  Bills:        25")
    print(f"  Alerts:       15")
    print()
    print("  All users password: Password123!")
    print("  Admin:        admin@hospify.com")
    print("  Doctor:       dr.khalid@hospify.com")
    print("  Nurse:        nurse.fatima@hospify.com")
    print("  Lab Tech:     lab.raza@hospify.com")
    print("  Pharmacist:   pharma.nadia@hospify.com")
    print("  Billing:      billing.zara@hospify.com")
    print("="*60)


if __name__ == "__main__":
    main()
