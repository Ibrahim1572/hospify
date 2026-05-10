"""
backend/app/patients/queries.py — Raw SQL queries for patients module
"""


def get_all_patients(cur, search=None):
    if search:
        cur.execute(
            """
            SELECT patient_id, full_name, dob, gender, cnic, phone, blood_group,
                   calculate_age(dob) AS age, created_at
              FROM patients
             WHERE full_name ILIKE %s OR cnic ILIKE %s
             ORDER BY full_name
            """,
            (f"%{search}%", f"%{search}%")
        )
    else:
        cur.execute(
            """
            SELECT patient_id, full_name, dob, gender, cnic, phone, blood_group,
                   calculate_age(dob) AS age, created_at
              FROM patients ORDER BY created_at DESC
            """
        )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_patient_by_id(cur, patient_id):
    cur.execute(
        """
        SELECT patient_id, full_name, dob, gender, cnic, phone, address,
               blood_group, emergency_contact,
               calculate_age(dob) AS age, created_at
          FROM patients WHERE patient_id = %s
        """,
        (patient_id,)
    )
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def create_patient(cur, data):
    cur.execute(
        """
        INSERT INTO patients(full_name, dob, gender, cnic, phone, address,
                             blood_group, emergency_contact)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING patient_id
        """,
        (
            data["full_name"], data["dob"], data["gender"],
            data["cnic"], data.get("phone"), data.get("address"),
            data.get("blood_group"), data.get("emergency_contact")
        )
    )
    return cur.fetchone()[0]


def update_patient(cur, patient_id, data):
    cur.execute(
        """
        UPDATE patients
           SET full_name = %s, dob = %s, gender = %s, cnic = %s, phone = %s,
               address = %s, blood_group = %s, emergency_contact = %s
         WHERE patient_id = %s
        """,
        (
            data["full_name"], data["dob"], data["gender"],
            data["cnic"], data.get("phone"), data.get("address"),
            data.get("blood_group"), data.get("emergency_contact"),
            patient_id
        )
    )


def delete_patient(cur, patient_id):
    cur.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))


# ── Subqueries ────────────────────────────────────────────────────────────────

def patients_admitted_3_times_last_year(cur):
    """Patients admitted more than 3 times in the last year (subquery demo)."""
    cur.execute(
        """
        SELECT p.patient_id, p.full_name, p.cnic, sub.admit_count
          FROM patients p
          JOIN (
              SELECT patient_id, COUNT(*) AS admit_count
                FROM admissions
               WHERE admitted_at >= NOW() - INTERVAL '1 year'
               GROUP BY patient_id
              HAVING COUNT(*) > 3
          ) sub ON sub.patient_id = p.patient_id
         ORDER BY sub.admit_count DESC
        """
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
