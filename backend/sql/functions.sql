-- ============================================================
-- Hospify HMS — SQL Functions (PL/pgSQL)
-- ============================================================

-- ------------------------------------------------------------
-- 1. Calculate patient age from date of birth
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION calculate_age(dob DATE)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN DATE_PART('year', AGE(CURRENT_DATE, dob))::INTEGER;
END;
$$;

-- ------------------------------------------------------------
-- 2. Calculate total bill amount for an admission
--    (sums bill_items.total_price for all bills of the admission)
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION calculate_bill_total(p_admission_id INT)
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
DECLARE
    v_total NUMERIC := 0;
BEGIN
    SELECT COALESCE(SUM(bi.total_price), 0)
      INTO v_total
      FROM bills b
      JOIN bill_items bi ON bi.bill_id = b.bill_id
     WHERE b.admission_id = p_admission_id;

    RETURN v_total;
END;
$$;

-- ------------------------------------------------------------
-- 3. Bed occupancy rate for a ward (returns percentage 0-100)
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION bed_occupancy_rate(p_ward_id INT)
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
DECLARE
    v_total    INT := 0;
    v_occupied INT := 0;
BEGIN
    SELECT COUNT(*),
           COUNT(*) FILTER (WHERE status = 'occupied')
      INTO v_total, v_occupied
      FROM beds
     WHERE ward_id = p_ward_id;

    IF v_total = 0 THEN
        RETURN 0;
    END IF;

    RETURN ROUND((v_occupied::NUMERIC / v_total) * 100, 2);
END;
$$;

-- ------------------------------------------------------------
-- 4. Average value of a specific vital for an admission
--    p_vital: 'temperature' | 'pulse' | 'oxygen_saturation' |
--             'blood_pressure_sys' | 'blood_pressure_dia' | 'weight'
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION average_vital(p_admission_id INT, p_vital TEXT)
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
DECLARE
    v_avg NUMERIC := 0;
    v_sql TEXT;
BEGIN
    -- Whitelist check to prevent SQL injection
    IF p_vital NOT IN ('temperature','blood_pressure_sys','blood_pressure_dia',
                       'pulse','oxygen_saturation','weight') THEN
        RAISE EXCEPTION 'Invalid vital name: %', p_vital;
    END IF;

    v_sql := format(
        'SELECT COALESCE(AVG(%I), 0) FROM vitals WHERE admission_id = $1',
        p_vital
    );
    EXECUTE v_sql INTO v_avg USING p_admission_id;
    RETURN ROUND(v_avg, 2);
END;
$$;
