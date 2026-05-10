"""
backend/seed/seed_data.py — Insert realistic HMS data into Postgres.
Run from project root (venv active): python backend/seed/seed_data.py
"""
import sys, os, random
from pathlib import Path
from datetime import date, datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from dotenv import load_dotenv
load_dotenv()
import psycopg2
from werkzeug.security import generate_password_hash

def connect():
    return psycopg2.connect(
        host=os.getenv("DB_HOST","localhost"), port=os.getenv("DB_PORT","5432"),
        dbname=os.getenv("DB_NAME","Hospify_DBMS"), user=os.getenv("DB_USER","postgres"),
        password=os.getenv("DB_PASSWORD","")
    )

def main():
    conn = connect(); conn.autocommit = False; cur = conn.cursor()

    # ── Users ────────────────────────────────────────────────────────────────
    print("Seeding users...")
    users = [
        ("Admin User","admin@hospify.com","super_admin"),
        ("Sara Ahmed","receptionist@hospify.com","receptionist"),
        ("Dr. Khalid Mir","dr.khalid@hospify.com","doctor"),
        ("Dr. Ayesha Raza","dr.ayesha@hospify.com","doctor"),
        ("Dr. Omar Farooq","dr.omar@hospify.com","doctor"),
        ("Nurse Fatima","nurse.fatima@hospify.com","nurse"),
        ("Nurse Bilal","nurse.bilal@hospify.com","nurse"),
        ("Tech Raza","lab.raza@hospify.com","lab_technician"),
        ("Pharma Nadia","pharma.nadia@hospify.com","pharmacist"),
        ("Billing Zara","billing.zara@hospify.com","billing_staff"),
    ]
    uid = {}
    for name,email,role in users:
        cur.execute(
            "INSERT INTO users(full_name,email,password_hash,role) VALUES(%s,%s,%s,%s) "
            "ON CONFLICT(email) DO UPDATE SET full_name=EXCLUDED.full_name RETURNING user_id",
            (name, email, generate_password_hash("Password123!"), role))
        uid[email] = cur.fetchone()[0]
    conn.commit()

    # ── Wards + Beds ─────────────────────────────────────────────────────────
    print("Seeding wards + beds...")
    ward_ids = []
    for wname,wtype,floor in [("General Ward A","general",1),("ICU","icu",2),("Pediatric Ward","pediatric",3)]:
        cur.execute(
            "INSERT INTO wards(ward_name,ward_type,floor_number,total_beds) VALUES(%s,%s,%s,7) "
            "ON CONFLICT DO NOTHING RETURNING ward_id", (wname,wtype,floor))
        r = cur.fetchone()
        if r: ward_ids.append(r[0])
    conn.commit()
    if not ward_ids:
        cur.execute("SELECT ward_id FROM wards ORDER BY ward_id LIMIT 3"); ward_ids=[r[0] for r in cur.fetchall()]

    bed_ids = []
    for wid in ward_ids:
        cur.execute("SELECT COUNT(*) FROM beds WHERE ward_id=%s",(wid,))
        if cur.fetchone()[0]==0:
            for i in range(1,8):
                cur.execute("INSERT INTO beds(ward_id,bed_number,bed_type) VALUES(%s,%s,'general') RETURNING bed_id",(wid,f"B{wid}-{i:02d}"))
                bed_ids.append(cur.fetchone()[0])
    conn.commit()
    if not bed_ids:
        cur.execute("SELECT bed_id FROM beds ORDER BY bed_id"); bed_ids=[r[0] for r in cur.fetchall()]

    # ── Doctors / Nurses / Tech / Pharma ─────────────────────────────────────
    print("Seeding staff...")
    doc_ids=[]
    for email,spec,qual,days in [
        ("dr.khalid@hospify.com","Cardiology","MBBS,FCPS","Mon,Tue,Wed,Thu"),
        ("dr.ayesha@hospify.com","Pediatrics","MBBS,MCPS","Tue,Wed,Thu,Fri"),
        ("dr.omar@hospify.com","General Surgery","MBBS,FRCS","Mon,Wed,Fri")]:
        cur.execute("INSERT INTO doctors(user_id,specialization,qualification,available_days) VALUES(%s,%s,%s,%s) "
            "ON CONFLICT(user_id) DO UPDATE SET specialization=EXCLUDED.specialization RETURNING doctor_id",(uid[email],spec,qual,days))
        doc_ids.append(cur.fetchone()[0])

    nurse_ids=[]
    for i,email in enumerate(["nurse.fatima@hospify.com","nurse.bilal@hospify.com"]):
        cur.execute("INSERT INTO nurses(user_id,ward_id,shift) VALUES(%s,%s,%s) "
            "ON CONFLICT(user_id) DO UPDATE SET shift=EXCLUDED.shift RETURNING nurse_id",
            (uid[email],ward_ids[i%len(ward_ids)],["morning","evening"][i%2]))
        nurse_ids.append(cur.fetchone()[0])

    cur.execute("INSERT INTO lab_technicians(user_id) VALUES(%s) ON CONFLICT(user_id) DO UPDATE SET user_id=EXCLUDED.user_id RETURNING tech_id",(uid["lab.raza@hospify.com"],))
    tech_id=cur.fetchone()[0]
    cur.execute("INSERT INTO pharmacists(user_id) VALUES(%s) ON CONFLICT(user_id) DO UPDATE SET user_id=EXCLUDED.user_id",(uid["pharma.nadia@hospify.com"],))
    conn.commit()

    # ── Patients ─────────────────────────────────────────────────────────────
    print("Seeding patients...")
    patients_raw=[
        ("Muhammad Ali",date(1985,3,15),"male","3520112345671","03001234567","Lahore","A+","Ali Sr 03009876543"),
        ("Fatima Khan",date(1992,7,22),"female","3520198765432","03111234567","Karachi","B+","Khan Sr 03111111111"),
        ("Ahmed Raza",date(1970,11,5),"male","3520287654321","03211234567","Islamabad","O+","Raza Mo 03212345678"),
        ("Zainab Malik",date(2005,2,10),"female","3520376543210","03311234567","Peshawar","AB+","Malik 03312345678"),
        ("Hassan Siddiqui",date(1958,9,30),"male","3520465432109","03411234567","Quetta","A-","Siddiqui 03412345678"),
        ("Amna Butt",date(1999,4,18),"female","3520554321098","03511234567","Faisalabad","B-","Butt 03512345678"),
        ("Usman Tariq",date(1945,12,1),"male","3520643210987","03611234567","Multan","O-","Tariq 03612345678"),
        ("Sana Iqbal",date(2010,6,25),"female","3520732109876","03711234567","Rawalpindi","AB-","Iqbal 03712345678"),
        ("Bilal Chaudhry",date(1988,8,14),"male","3520821098765","03811234567","Sialkot","A+","Chaudhry 03812345678"),
        ("Maryam Sher",date(1975,1,3),"female","3520910987654","03911234567","Gujranwala","B+","Sher 03912345678"),
    ]
    pat_ids=[]
    for p in patients_raw:
        cur.execute("INSERT INTO patients(full_name,dob,gender,cnic,phone,address,blood_group,emergency_contact) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(cnic) DO UPDATE SET full_name=EXCLUDED.full_name RETURNING patient_id",p)
        pat_ids.append(cur.fetchone()[0])
    conn.commit()

    # ── Medicines ─────────────────────────────────────────────────────────────
    print("Seeding medicines (50)...")
    med_list=[
        ("Paracetamol","Panadol","Analgesic","tablet"),("Amoxicillin","Amoxil","Antibiotic","capsule"),
        ("Metformin","Glucophage","Antidiabetic","tablet"),("Amlodipine","Norvasc","Antihypertensive","tablet"),
        ("Omeprazole","Losec","PPI","capsule"),("Atorvastatin","Lipitor","Statin","tablet"),
        ("Ibuprofen","Brufen","NSAID","tablet"),("Ciprofloxacin","Cipro","Antibiotic","tablet"),
        ("Losartan","Cozaar","ARB","tablet"),("Pantoprazole","Protonix","PPI","tablet"),
        ("Salbutamol","Ventolin","Bronchodilator","inhaler"),("Metronidazole","Flagyl","Antibiotic","tablet"),
        ("Dexamethasone","Decadron","Steroid","injection"),("Furosemide","Lasix","Diuretic","tablet"),
        ("Warfarin","Coumadin","Anticoagulant","tablet"),("Ceftriaxone","Rocephin","Antibiotic","injection"),
        ("Morphine","MS Contin","Opioid","injection"),("Insulin Glargine","Lantus","Insulin","injection"),
        ("Aspirin","Ecotrin","Antiplatelet","tablet"),("Ranitidine","Zantac","H2 Blocker","tablet"),
        ("Lisinopril","Prinivil","ACE Inhibitor","tablet"),("Enalapril","Vasotec","ACE Inhibitor","tablet"),
        ("Hydrochlorothiazide","Microzide","Diuretic","tablet"),("Simvastatin","Zocor","Statin","tablet"),
        ("Clopidogrel","Plavix","Antiplatelet","tablet"),("Ramipril","Altace","ACE Inhibitor","tablet"),
        ("Bisoprolol","Zebeta","Beta Blocker","tablet"),("Carvedilol","Coreg","Beta Blocker","tablet"),
        ("Diltiazem","Cardizem","CCB","tablet"),("Verapamil","Calan","CCB","tablet"),
        ("Spironolactone","Aldactone","Diuretic","tablet"),("Digoxin","Lanoxin","Cardiac Glycoside","tablet"),
        ("Heparin","Heparin","Anticoagulant","injection"),("Enoxaparin","Clexane","Anticoagulant","injection"),
        ("Ondansetron","Zofran","Antiemetic","tablet"),("Domperidone","Motilium","Antiemetic","tablet"),
        ("Loperamide","Imodium","Antidiarrheal","capsule"),("Cetirizine","Zyrtec","Antihistamine","tablet"),
        ("Loratadine","Claritin","Antihistamine","tablet"),("Montelukast","Singulair","Leukotriene antagonist","tablet"),
        ("Fluticasone","Flixotide","Corticosteroid","inhaler"),("Tiotropium","Spiriva","Anticholinergic","inhaler"),
        ("Amitriptyline","Elavil","Antidepressant","tablet"),("Sertraline","Zoloft","SSRI","tablet"),
        ("Diazepam","Valium","Benzodiazepine","tablet"),("Phenytoin","Dilantin","Anticonvulsant","tablet"),
        ("Levetiracetam","Keppra","Anticonvulsant","tablet"),("Tramadol","Ultram","Analgesic","capsule"),
        ("Ketorolac","Toradol","NSAID","injection"),("Prednisolone","Prelone","Steroid","tablet"),
    ]
    med_ids=[]
    for g,b,cat,unit in med_list:
        cur.execute("INSERT INTO medicines(generic_name,brand_name,category,unit) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING medicine_id",(g,b,cat,unit))
        r=cur.fetchone()
        if r: med_ids.append(r[0])
    conn.commit()
    if not med_ids:
        cur.execute("SELECT medicine_id FROM medicines ORDER BY medicine_id LIMIT 50"); med_ids=[r[0] for r in cur.fetchall()]
    for mid in med_ids:
        qty=random.randint(5,300)
        cur.execute("INSERT INTO medicine_inventory(medicine_id,quantity_available,reorder_level) VALUES(%s,%s,15) ON CONFLICT(medicine_id) DO UPDATE SET quantity_available=EXCLUDED.quantity_available",(mid,qty))
    conn.commit()

    # ── Admissions (20) ───────────────────────────────────────────────────────
    print("Seeding admissions...")
    adm_ids=[]
    # Disable triggers during seed to avoid cascading conflicts
    cur.execute("SET session_replication_role = 'replica'")
    shuffled_beds=list(bed_ids); random.shuffle(shuffled_beds)
    # Use each bed at most once for active admissions
    active_beds  = shuffled_beds[:10]
    inactive_beds= shuffled_beds[10:] if len(shuffled_beds)>10 else shuffled_beds
    for i in range(20):
        pid=pat_ids[i%len(pat_ids)]; did=doc_ids[i%len(doc_ids)]
        days_ago=random.randint(1,60); admit_dt=datetime.now()-timedelta(days=days_ago)
        if i<10:
            bid=active_beds[i%len(active_beds)]
            cur.execute(
                "INSERT INTO admissions(patient_id,bed_id,doctor_id,admission_type,status,admitted_at) "
                "VALUES(%s,%s,%s,'general','active',%s) RETURNING admission_id",
                (pid,bid,did,admit_dt))
            row=cur.fetchone()
            if row:
                adm_ids.append(row[0])
                cur.execute("UPDATE beds SET status='occupied' WHERE bed_id=%s",(bid,))
        else:
            bid=inactive_beds[i%len(inactive_beds)] if inactive_beds else active_beds[i%len(active_beds)]
            dis_dt=admit_dt+timedelta(days=random.randint(2,10))
            cur.execute(
                "INSERT INTO admissions(patient_id,bed_id,doctor_id,admission_type,status,admitted_at,discharged_at) "
                "VALUES(%s,%s,%s,'general','discharged',%s,%s) RETURNING admission_id",
                (pid,bid,did,admit_dt,dis_dt))
            row=cur.fetchone()
            if row: adm_ids.append(row[0])
    cur.execute("SET session_replication_role = 'origin'")
    conn.commit()

    # ── Vitals ────────────────────────────────────────────────────────────────
    print("Seeding vitals...")
    for aid in adm_ids[:10]:
        for _ in range(random.randint(2,5)):
            cur.execute("INSERT INTO vitals(admission_id,nurse_id,temperature,blood_pressure_sys,blood_pressure_dia,pulse,oxygen_saturation,weight) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (aid,nurse_ids[0],round(random.uniform(36.5,38.5),1),random.randint(110,140),random.randint(70,90),random.randint(60,100),round(random.uniform(94,99),1),round(random.uniform(55,90),1)))
    conn.commit()

    # ── Prescriptions (30) ────────────────────────────────────────────────────
    print("Seeding prescriptions...")
    for i in range(30):
        aid=adm_ids[i%len(adm_ids)]; did=doc_ids[i%len(doc_ids)]
        cur.execute("INSERT INTO prescriptions(admission_id,doctor_id,notes) VALUES(%s,%s,%s) RETURNING prescription_id",(aid,did,f"Rx #{i+1}"))
        rx_id=cur.fetchone()[0]
        for j in range(random.randint(1,3)):
            mid=med_ids[(i+j)%len(med_ids)]
            cur.execute("INSERT INTO prescription_items(prescription_id,medicine_id,dosage,frequency,duration_days) VALUES(%s,%s,%s,%s,%s)",(rx_id,mid,"1 tab","Twice daily",random.randint(3,14)))
    conn.commit()

    # ── Lab orders + results (20) ─────────────────────────────────────────────
    print("Seeding lab orders...")
    tests=["CBC","LFTs","RFTs","Blood Culture","Urine RE","ECG","Chest X-Ray","Blood Sugar","Lipid Profile","Thyroid Panel"]
    for i in range(20):
        aid=adm_ids[i%len(adm_ids)]; did=doc_ids[i%len(doc_ids)]
        cur.execute("INSERT INTO lab_orders(admission_id,doctor_id,test_name,priority,status) VALUES(%s,%s,%s,%s,'completed') RETURNING order_id",
            (aid,did,random.choice(tests),random.choice(["routine","urgent","stat"])))
        oid=cur.fetchone()[0]
        cur.execute("INSERT INTO lab_results(order_id,tech_id,result_summary) VALUES(%s,%s,%s)",(oid,tech_id,"All values within normal reference ranges."))
    conn.commit()

    # ── Bills + Payments (10) ─────────────────────────────────────────────────
    print("Seeding bills + payments...")
    billing_uid=uid["billing.zara@hospify.com"]
    for i in range(10):
        aid=adm_ids[i+10]
        total=random.randint(5000,25000)
        cur.execute("INSERT INTO bills(admission_id,generated_by,total_amount,paid_amount,status) VALUES(%s,%s,%s,%s,'paid') ON CONFLICT DO NOTHING RETURNING bill_id",(aid,billing_uid,total,total))
        r=cur.fetchone()
        if r:
            bill_id=r[0]
            cur.execute("INSERT INTO bill_items(bill_id,service_type,description,quantity,unit_price) VALUES(%s,'bed','Bed + services',3,2000)",(bill_id,))
            cur.execute("INSERT INTO payments(bill_id,amount,payment_method,received_by) VALUES(%s,%s,'cash',%s)",(bill_id,total,billing_uid))
    conn.commit()
    cur.close(); conn.close()
    print("\n[OK] Seed data inserted successfully!\n")
    print("   Login credentials -- all users: Password123!")
    print("   Admin: admin@hospify.com | Doctor: dr.khalid@hospify.com")

if __name__=="__main__":
    main()
