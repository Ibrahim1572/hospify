-- ============================================================
-- Hospify HMS — Views
-- ============================================================

-- ------------------------------------------------------------
-- 1. All currently active admissions (patient + doctor + ward + bed)
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW active_admissions_view AS
SELECT
    a.admission_id,
    a.admitted_at,
    a.admission_type,
    a.notes                                   AS admission_notes,
    p.patient_id,
    p.full_name                               AS patient_name,
    p.gender,
    p.blood_group,
    calculate_age(p.dob)                      AS patient_age,
    p.phone                                   AS patient_phone,
    d.doctor_id,
    u_doc.full_name                           AS doctor_name,
    d.specialization,
    b.bed_id,
    b.bed_number,
    b.bed_type,
    w.ward_id,
    w.ward_name,
    w.ward_type,
    w.floor_number
FROM admissions a
JOIN patients   p    ON p.patient_id  = a.patient_id
JOIN doctors    d    ON d.doctor_id   = a.doctor_id
JOIN users      u_doc ON u_doc.user_id = d.user_id
JOIN beds       b    ON b.bed_id      = a.bed_id
JOIN wards      w    ON w.ward_id     = b.ward_id
WHERE a.status = 'active';

-- ------------------------------------------------------------
-- 2. Today's doctor schedule with appointment count
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW doctor_schedule_today AS
SELECT
    d.doctor_id,
    u.full_name                                  AS doctor_name,
    d.specialization,
    COUNT(ap.appointment_id)                     AS total_appointments,
    COUNT(ap.appointment_id) FILTER (WHERE ap.status = 'scheduled')   AS pending,
    COUNT(ap.appointment_id) FILTER (WHERE ap.status = 'completed')   AS completed,
    COUNT(ap.appointment_id) FILTER (WHERE ap.status = 'cancelled')   AS cancelled
FROM doctors d
JOIN users u ON u.user_id = d.user_id
LEFT JOIN appointments ap
    ON ap.doctor_id = d.doctor_id
   AND ap.scheduled_at::DATE = CURRENT_DATE
GROUP BY d.doctor_id, u.full_name, d.specialization;

-- ------------------------------------------------------------
-- 3. All pending lab orders with patient name and priority
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW pending_lab_orders_view AS
SELECT
    lo.order_id,
    lo.test_name,
    lo.priority,
    lo.ordered_at,
    lo.status,
    p.patient_id,
    p.full_name  AS patient_name,
    a.admission_id,
    u_doc.full_name AS ordering_doctor
FROM lab_orders lo
JOIN admissions a   ON a.admission_id = lo.admission_id
JOIN patients   p   ON p.patient_id   = a.patient_id
JOIN doctors    d   ON d.doctor_id    = lo.doctor_id
JOIN users   u_doc  ON u_doc.user_id  = d.user_id
WHERE lo.status IN ('pending','in_progress')
ORDER BY
    CASE lo.priority WHEN 'stat' THEN 1 WHEN 'urgent' THEN 2 ELSE 3 END,
    lo.ordered_at;

-- ------------------------------------------------------------
-- 4. Ward occupancy summary
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW ward_occupancy_view AS
SELECT
    w.ward_id,
    w.ward_name,
    w.ward_type,
    w.floor_number,
    COUNT(b.bed_id)                                              AS total_beds,
    COUNT(b.bed_id) FILTER (WHERE b.status = 'occupied')        AS occupied_beds,
    COUNT(b.bed_id) FILTER (WHERE b.status = 'available')       AS available_beds,
    COUNT(b.bed_id) FILTER (WHERE b.status = 'maintenance')     AS maintenance_beds,
    bed_occupancy_rate(w.ward_id)                                AS occupancy_rate_pct
FROM wards w
LEFT JOIN beds b ON b.ward_id = w.ward_id
GROUP BY w.ward_id, w.ward_name, w.ward_type, w.floor_number;

-- ------------------------------------------------------------
-- 5. Top prescribed medicines this month
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW top_medicines_this_month AS
SELECT
    m.medicine_id,
    m.generic_name,
    m.brand_name,
    m.category,
    COUNT(pi.item_id)             AS prescription_count,
    mi.quantity_available
FROM prescription_items pi
JOIN medicines         m  ON m.medicine_id   = pi.medicine_id
LEFT JOIN medicine_inventory mi ON mi.medicine_id = m.medicine_id
JOIN prescriptions     px ON px.prescription_id = pi.prescription_id
WHERE DATE_TRUNC('month', px.prescribed_at) = DATE_TRUNC('month', CURRENT_DATE)
GROUP BY m.medicine_id, m.generic_name, m.brand_name, m.category, mi.quantity_available
ORDER BY prescription_count DESC;
