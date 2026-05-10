-- ============================================================
-- Hospify HMS — Database Schema
-- All tables normalized to 3NF, in FK-safe creation order
-- ============================================================

-- Enable pgcrypto for password hashing if desired
-- CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ------------------------------------------------------------
-- USERS & ROLES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id       SERIAL PRIMARY KEY,
    full_name     VARCHAR(150) NOT NULL,
    email         VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(50)  NOT NULL CHECK (role IN (
                      'super_admin','receptionist','doctor',
                      'nurse','lab_technician','pharmacist','billing_staff')),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- PATIENTS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    patient_id        SERIAL PRIMARY KEY,
    full_name         VARCHAR(150) NOT NULL,
    dob               DATE         NOT NULL,
    gender            VARCHAR(10)  NOT NULL CHECK (gender IN ('male','female','other')),
    cnic              VARCHAR(15)  UNIQUE NOT NULL,
    phone             VARCHAR(20),
    address           TEXT,
    blood_group       VARCHAR(5),
    emergency_contact VARCHAR(100),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- WARDS & BEDS
-- (must exist before staff tables that FK to ward_id)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wards (
    ward_id     SERIAL PRIMARY KEY,
    ward_name   VARCHAR(100) NOT NULL,
    ward_type   VARCHAR(50)  NOT NULL,
    floor_number INT,
    total_beds  INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS beds (
    bed_id      SERIAL PRIMARY KEY,
    ward_id     INT NOT NULL REFERENCES wards(ward_id) ON DELETE CASCADE,
    bed_number  VARCHAR(20) NOT NULL,
    bed_type    VARCHAR(50),
    status      VARCHAR(20) NOT NULL DEFAULT 'available'
                    CHECK (status IN ('available','occupied','maintenance')),
    UNIQUE (ward_id, bed_number)
);

-- ------------------------------------------------------------
-- STAFF
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doctors (
    doctor_id      SERIAL PRIMARY KEY,
    user_id        INT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    specialization VARCHAR(100),
    qualification  VARCHAR(150),
    phone          VARCHAR(20),
    available_days VARCHAR(100)   -- e.g. 'Mon,Tue,Wed'
);

CREATE TABLE IF NOT EXISTS nurses (
    nurse_id SERIAL PRIMARY KEY,
    user_id  INT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    ward_id  INT REFERENCES wards(ward_id) ON DELETE SET NULL,
    shift    VARCHAR(20) CHECK (shift IN ('morning','evening','night'))
);

CREATE TABLE IF NOT EXISTS lab_technicians (
    tech_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pharmacists (
    pharmacist_id SERIAL PRIMARY KEY,
    user_id       INT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- ADMISSIONS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admissions (
    admission_id   SERIAL PRIMARY KEY,
    patient_id     INT NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    bed_id         INT REFERENCES beds(bed_id) ON DELETE SET NULL,
    doctor_id      INT REFERENCES doctors(doctor_id) ON DELETE SET NULL,
    admitted_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    discharged_at  TIMESTAMPTZ,
    admission_type VARCHAR(50)  NOT NULL DEFAULT 'general',
    status         VARCHAR(20)  NOT NULL DEFAULT 'active'
                       CHECK (status IN ('active','discharged','transferred')),
    notes          TEXT
);

-- ------------------------------------------------------------
-- APPOINTMENTS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id SERIAL PRIMARY KEY,
    patient_id     INT NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    doctor_id      INT NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
    scheduled_at   TIMESTAMPTZ  NOT NULL,
    status         VARCHAR(20)  NOT NULL DEFAULT 'scheduled'
                       CHECK (status IN ('scheduled','completed','cancelled','no_show')),
    reason         TEXT
);

-- ------------------------------------------------------------
-- VITALS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vitals (
    vital_id              SERIAL PRIMARY KEY,
    admission_id          INT NOT NULL REFERENCES admissions(admission_id) ON DELETE CASCADE,
    nurse_id              INT REFERENCES nurses(nurse_id) ON DELETE SET NULL,
    recorded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    temperature           NUMERIC(5,2),
    blood_pressure_sys    INT,
    blood_pressure_dia    INT,
    pulse                 INT,
    oxygen_saturation     NUMERIC(5,2),
    weight                NUMERIC(6,2),
    notes                 TEXT
);

-- ------------------------------------------------------------
-- MEDICINES & INVENTORY
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medicines (
    medicine_id  SERIAL PRIMARY KEY,
    generic_name VARCHAR(150) NOT NULL,
    brand_name   VARCHAR(150),
    category     VARCHAR(100),
    unit         VARCHAR(30),
    description  TEXT
);

CREATE TABLE IF NOT EXISTS medicine_inventory (
    inventory_id       SERIAL PRIMARY KEY,
    medicine_id        INT NOT NULL UNIQUE REFERENCES medicines(medicine_id) ON DELETE CASCADE,
    quantity_available INT NOT NULL DEFAULT 0,
    reorder_level      INT NOT NULL DEFAULT 10,
    last_updated       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- PRESCRIPTIONS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prescriptions (
    prescription_id SERIAL PRIMARY KEY,
    admission_id    INT NOT NULL REFERENCES admissions(admission_id) ON DELETE CASCADE,
    doctor_id       INT NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
    prescribed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS prescription_items (
    item_id         SERIAL PRIMARY KEY,
    prescription_id INT NOT NULL REFERENCES prescriptions(prescription_id) ON DELETE CASCADE,
    medicine_id     INT NOT NULL REFERENCES medicines(medicine_id) ON DELETE CASCADE,
    dosage          VARCHAR(50),
    frequency       VARCHAR(50),
    duration_days   INT,
    instructions    TEXT
);

-- ------------------------------------------------------------
-- MEDIA FILES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS media_files (
    file_id      SERIAL PRIMARY KEY,
    entity_type  VARCHAR(50),   -- 'patient', 'lab_result', etc.
    entity_id    INT,
    file_name    VARCHAR(255),
    file_type    VARCHAR(50),   -- 'jpeg','pdf','png'
    file_data    BYTEA,
    firebase_url TEXT,
    uploaded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    uploaded_by  INT REFERENCES users(user_id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- LAB
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lab_orders (
    order_id     SERIAL PRIMARY KEY,
    admission_id INT NOT NULL REFERENCES admissions(admission_id) ON DELETE CASCADE,
    doctor_id    INT NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
    test_name    VARCHAR(150) NOT NULL,
    ordered_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    status       VARCHAR(20)  NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending','in_progress','completed','cancelled')),
    priority     VARCHAR(20)  NOT NULL DEFAULT 'routine'
                     CHECK (priority IN ('routine','urgent','stat'))
);

CREATE TABLE IF NOT EXISTS lab_results (
    result_id      SERIAL PRIMARY KEY,
    order_id       INT NOT NULL UNIQUE REFERENCES lab_orders(order_id) ON DELETE CASCADE,
    tech_id        INT REFERENCES lab_technicians(tech_id) ON DELETE SET NULL,
    result_summary TEXT,
    result_file_id INT REFERENCES media_files(file_id) ON DELETE SET NULL,
    resulted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes          TEXT
);

-- ------------------------------------------------------------
-- BILLING
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bills (
    bill_id      SERIAL PRIMARY KEY,
    admission_id INT NOT NULL REFERENCES admissions(admission_id) ON DELETE CASCADE,
    generated_by INT REFERENCES users(user_id) ON DELETE SET NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    discount     NUMERIC(12,2) NOT NULL DEFAULT 0,
    paid_amount  NUMERIC(12,2) NOT NULL DEFAULT 0,
    status       VARCHAR(20)  NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending','partial','paid','waived'))
);

CREATE TABLE IF NOT EXISTS bill_items (
    bill_item_id SERIAL PRIMARY KEY,
    bill_id      INT NOT NULL REFERENCES bills(bill_id) ON DELETE CASCADE,
    service_type VARCHAR(100),
    description  TEXT,
    quantity     INT NOT NULL DEFAULT 1,
    unit_price   NUMERIC(10,2) NOT NULL DEFAULT 0,
    total_price  NUMERIC(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id     SERIAL PRIMARY KEY,
    bill_id        INT NOT NULL REFERENCES bills(bill_id) ON DELETE CASCADE,
    paid_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    amount         NUMERIC(12,2) NOT NULL,
    payment_method VARCHAR(50)  NOT NULL DEFAULT 'cash'
                       CHECK (payment_method IN ('cash','card','bank_transfer','insurance')),
    received_by    INT REFERENCES users(user_id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- ALERTS & AUDIT
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    alert_id    SERIAL PRIMARY KEY,
    alert_type  VARCHAR(100) NOT NULL,
    entity_id   INT,
    message     TEXT NOT NULL,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id     SERIAL PRIMARY KEY,
    user_id    INT REFERENCES users(user_id) ON DELETE SET NULL,
    action     VARCHAR(50)  NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    record_id  INT,
    timestamp  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    old_value  JSONB,
    new_value  JSONB
);
