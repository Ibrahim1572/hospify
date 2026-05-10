-- ============================================================
-- Hospify HMS — Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_patients_cnic       ON patients(cnic);
CREATE INDEX IF NOT EXISTS idx_patients_name       ON patients(full_name);
CREATE INDEX IF NOT EXISTS idx_admissions_status   ON admissions(status);
CREATE INDEX IF NOT EXISTS idx_admissions_patient  ON admissions(patient_id);
CREATE INDEX IF NOT EXISTS idx_lab_orders_status   ON lab_orders(status);
CREATE INDEX IF NOT EXISTS idx_appointments_sched  ON appointments(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_medicines_name      ON medicines(generic_name);
CREATE INDEX IF NOT EXISTS idx_beds_status         ON beds(status);
CREATE INDEX IF NOT EXISTS idx_users_email         ON users(email);
CREATE INDEX IF NOT EXISTS idx_bills_status        ON bills(status);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved     ON alerts(is_resolved);
CREATE INDEX IF NOT EXISTS idx_audit_log_user      ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_vitals_admission    ON vitals(admission_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_adm   ON prescriptions(admission_id);
