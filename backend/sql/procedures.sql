-- ============================================================
-- Hospify HMS — Stored Procedures
-- Uses PL/pgSQL DECLARE / BEGIN / EXCEPTION / END pattern
-- ============================================================

-- ------------------------------------------------------------
-- 1. Discharge Patient
--    - Sets admission status to 'discharged'
--    - Sets discharged_at timestamp
--    - Frees the bed (status → available)
--    - Finalizes any pending bills
--    - All-or-nothing transaction
-- ------------------------------------------------------------
CREATE OR REPLACE PROCEDURE discharge_patient(p_admission_id INT, p_discharged_by INT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_bed_id INT;
    v_bill_id INT;
BEGIN
    -- Retrieve the bed associated with this admission
    SELECT bed_id INTO v_bed_id
      FROM admissions
     WHERE admission_id = p_admission_id AND status = 'active';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Admission % is not active or does not exist', p_admission_id;
    END IF;

    -- Update admission record
    UPDATE admissions
       SET status        = 'discharged',
           discharged_at = NOW()
     WHERE admission_id = p_admission_id;

    -- Free the bed
    IF v_bed_id IS NOT NULL THEN
        UPDATE beds SET status = 'available' WHERE bed_id = v_bed_id;
    END IF;

    -- Finalize any pending bills (mark as 'pending' ready for payment collection)
    UPDATE bills
       SET total_amount = calculate_bill_total(p_admission_id)
     WHERE admission_id = p_admission_id
       AND status = 'pending';

    -- Audit log
    INSERT INTO audit_log(user_id, action, table_name, record_id, new_value)
    VALUES (p_discharged_by, 'DISCHARGE', 'admissions', p_admission_id,
            jsonb_build_object('discharged_by', p_discharged_by, 'discharged_at', NOW()));

EXCEPTION
    WHEN OTHERS THEN
        RAISE;
END;
$$;

-- ------------------------------------------------------------
-- 2. Admit Patient
--    - Creates an admission record
--    - Marks the bed as occupied
--    - Validates bed is available
--    - All-or-nothing transaction
-- ------------------------------------------------------------
CREATE OR REPLACE PROCEDURE admit_patient(
    p_patient_id INT,
    p_bed_id     INT,
    p_doctor_id  INT,
    p_type       TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_bed_status VARCHAR(20);
    v_new_admission_id INT;
BEGIN
    -- Check bed availability
    SELECT status INTO v_bed_status FROM beds WHERE bed_id = p_bed_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Bed % does not exist', p_bed_id;
    END IF;

    IF v_bed_status <> 'available' THEN
        RAISE EXCEPTION 'Bed % is not available (status: %)', p_bed_id, v_bed_status;
    END IF;

    -- Create admission record
    INSERT INTO admissions(patient_id, bed_id, doctor_id, admission_type, status, admitted_at)
    VALUES (p_patient_id, p_bed_id, p_doctor_id, p_type, 'active', NOW())
    RETURNING admission_id INTO v_new_admission_id;

    -- Mark bed as occupied (trigger also does this, but explicit for clarity)
    UPDATE beds SET status = 'occupied' WHERE bed_id = p_bed_id;

    -- Audit log
    INSERT INTO audit_log(user_id, action, table_name, record_id, new_value)
    VALUES (NULL, 'ADMIT', 'admissions', v_new_admission_id,
            jsonb_build_object('patient_id', p_patient_id, 'bed_id', p_bed_id,
                               'doctor_id', p_doctor_id, 'type', p_type));

EXCEPTION
    WHEN OTHERS THEN
        RAISE;
END;
$$;

-- ------------------------------------------------------------
-- 3. Generate Itemized Bill
--    - Calculates charges from: bed days, lab orders, prescriptions
--    - Inserts bill + bill_items
--    - All-or-nothing transaction
-- ------------------------------------------------------------
CREATE OR REPLACE PROCEDURE generate_bill(p_admission_id INT, p_generated_by INT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_bill_id      INT;
    v_days         INT := 1;
    v_admitted_at  TIMESTAMPTZ;
    v_discharged_at TIMESTAMPTZ;
    v_lab_count    INT := 0;
    v_rx_count     INT := 0;
    v_total        NUMERIC := 0;
    v_bed_rate     NUMERIC := 2000;  -- PKR per day
    v_lab_rate     NUMERIC := 500;
    v_rx_rate      NUMERIC := 300;
BEGIN
    -- Check for existing bill
    SELECT bill_id INTO v_bill_id FROM bills WHERE admission_id = p_admission_id;
    IF FOUND THEN
        RAISE EXCEPTION 'Bill already exists for admission %', p_admission_id;
    END IF;

    -- Get admission duration
    SELECT admitted_at, discharged_at
      INTO v_admitted_at, v_discharged_at
      FROM admissions WHERE admission_id = p_admission_id;

    v_days := GREATEST(
        DATE_PART('day', COALESCE(v_discharged_at, NOW()) - v_admitted_at)::INT,
        1
    );

    -- Count lab orders
    SELECT COUNT(*) INTO v_lab_count FROM lab_orders WHERE admission_id = p_admission_id;

    -- Count prescription items
    SELECT COUNT(*) INTO v_rx_count
      FROM prescription_items pi
      JOIN prescriptions p ON p.prescription_id = pi.prescription_id
     WHERE p.admission_id = p_admission_id;

    v_total := (v_days * v_bed_rate) + (v_lab_count * v_lab_rate) + (v_rx_count * v_rx_rate);

    -- Create bill header
    INSERT INTO bills(admission_id, generated_by, generated_at, total_amount, status)
    VALUES (p_admission_id, p_generated_by, NOW(), v_total, 'pending')
    RETURNING bill_id INTO v_bill_id;

    -- Insert bill items: bed charges
    INSERT INTO bill_items(bill_id, service_type, description, quantity, unit_price)
    VALUES (v_bill_id, 'bed', format('Bed charges (%s days)', v_days), v_days, v_bed_rate);

    -- Insert bill items: lab charges
    IF v_lab_count > 0 THEN
        INSERT INTO bill_items(bill_id, service_type, description, quantity, unit_price)
        VALUES (v_bill_id, 'lab', format('Lab tests (%s orders)', v_lab_count), v_lab_count, v_lab_rate);
    END IF;

    -- Insert bill items: pharmacy charges
    IF v_rx_count > 0 THEN
        INSERT INTO bill_items(bill_id, service_type, description, quantity, unit_price)
        VALUES (v_bill_id, 'pharmacy', format('Prescribed medicines (%s items)', v_rx_count), v_rx_count, v_rx_rate);
    END IF;

    -- Audit
    INSERT INTO audit_log(user_id, action, table_name, record_id, new_value)
    VALUES (p_generated_by, 'GENERATE_BILL', 'bills', v_bill_id,
            jsonb_build_object('admission_id', p_admission_id, 'total', v_total));

EXCEPTION
    WHEN OTHERS THEN
        RAISE;
END;
$$;
