-- ============================================================
-- Hospify HMS — Triggers
-- ============================================================

-- ------------------------------------------------------------
-- Helper: generic audit log insert function
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_audit_log()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO audit_log(user_id, action, table_name, record_id, old_value, new_value)
    VALUES (
        current_setting('app.current_user_id', TRUE)::INT,
        TG_OP,
        TG_TABLE_NAME,
        CASE WHEN TG_OP = 'DELETE' THEN OLD.admission_id ELSE NEW.admission_id END,
        CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN row_to_json(OLD)::JSONB ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN row_to_json(NEW)::JSONB ELSE NULL END
    );
    RETURN NEW;
END;
$$;

-- ------------------------------------------------------------
-- TRIGGER 1: On bed assignment → mark bed as occupied
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_bed_on_assign()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.bed_id IS NOT NULL AND (OLD.bed_id IS DISTINCT FROM NEW.bed_id OR TG_OP = 'INSERT') THEN
        UPDATE beds SET status = 'occupied' WHERE bed_id = NEW.bed_id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_bed_on_assign ON admissions;
CREATE TRIGGER trg_bed_on_assign
    AFTER INSERT OR UPDATE OF bed_id ON admissions
    FOR EACH ROW EXECUTE FUNCTION fn_bed_on_assign();

-- ------------------------------------------------------------
-- TRIGGER 2: On discharge → mark bed as available
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_bed_on_discharge()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status = 'discharged' AND OLD.status <> 'discharged' AND OLD.bed_id IS NOT NULL THEN
        UPDATE beds SET status = 'available' WHERE bed_id = OLD.bed_id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_bed_on_discharge ON admissions;
CREATE TRIGGER trg_bed_on_discharge
    AFTER UPDATE OF status ON admissions
    FOR EACH ROW EXECUTE FUNCTION fn_bed_on_discharge();

-- ------------------------------------------------------------
-- TRIGGER 3: On medicine dispensed → decrement inventory
--   Fires when a prescription_item is inserted
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_decrement_inventory()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE medicine_inventory
       SET quantity_available = GREATEST(quantity_available - 1, 0),
           last_updated = NOW()
     WHERE medicine_id = NEW.medicine_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_decrement_inventory ON prescription_items;
CREATE TRIGGER trg_decrement_inventory
    AFTER INSERT ON prescription_items
    FOR EACH ROW EXECUTE FUNCTION fn_decrement_inventory();

-- ------------------------------------------------------------
-- TRIGGER 4: On inventory quantity < reorder_level → insert alert
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_low_stock_alert()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_name TEXT;
BEGIN
    IF NEW.quantity_available < NEW.reorder_level THEN
        SELECT generic_name INTO v_name FROM medicines WHERE medicine_id = NEW.medicine_id;
        INSERT INTO alerts(alert_type, entity_id, message)
        VALUES ('low_stock', NEW.medicine_id,
                format('Low stock: %s — only %s units remaining (reorder level: %s)',
                       v_name, NEW.quantity_available, NEW.reorder_level));
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_low_stock_alert ON medicine_inventory;
CREATE TRIGGER trg_low_stock_alert
    AFTER UPDATE OF quantity_available ON medicine_inventory
    FOR EACH ROW EXECUTE FUNCTION fn_low_stock_alert();

-- ------------------------------------------------------------
-- TRIGGER 5: On admission INSERT/UPDATE → audit log
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_admission_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO audit_log(user_id, action, table_name, record_id, old_value, new_value)
    VALUES (
        NULL,  -- user context set via app.current_user_id if available
        TG_OP,
        'admissions',
        CASE WHEN TG_OP = 'DELETE' THEN OLD.admission_id ELSE NEW.admission_id END,
        CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN row_to_json(OLD)::JSONB ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN row_to_json(NEW)::JSONB ELSE NULL END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS trg_admission_audit ON admissions;
CREATE TRIGGER trg_admission_audit
    AFTER INSERT OR UPDATE OR DELETE ON admissions
    FOR EACH ROW EXECUTE FUNCTION fn_admission_audit();

-- ------------------------------------------------------------
-- TRIGGER 6: On vitals insert with abnormal values → insert alert
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_abnormal_vitals_alert()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_patient_name TEXT;
BEGIN
    SELECT p.full_name INTO v_patient_name
      FROM admissions a
      JOIN patients p ON p.patient_id = a.patient_id
     WHERE a.admission_id = NEW.admission_id;

    IF NEW.temperature IS NOT NULL AND (NEW.temperature < 35 OR NEW.temperature > 39.5) THEN
        INSERT INTO alerts(alert_type, entity_id, message)
        VALUES ('abnormal_vital', NEW.admission_id,
                format('Abnormal temperature %.1f°C for patient %s (admission %s)',
                       NEW.temperature, v_patient_name, NEW.admission_id));
    END IF;

    IF NEW.oxygen_saturation IS NOT NULL AND NEW.oxygen_saturation < 94 THEN
        INSERT INTO alerts(alert_type, entity_id, message)
        VALUES ('abnormal_vital', NEW.admission_id,
                format('Low SpO2 %.1f%% for patient %s (admission %s)',
                       NEW.oxygen_saturation, v_patient_name, NEW.admission_id));
    END IF;

    IF NEW.pulse IS NOT NULL AND (NEW.pulse < 50 OR NEW.pulse > 120) THEN
        INSERT INTO alerts(alert_type, entity_id, message)
        VALUES ('abnormal_vital', NEW.admission_id,
                format('Abnormal pulse %s bpm for patient %s (admission %s)',
                       NEW.pulse, v_patient_name, NEW.admission_id));
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_abnormal_vitals ON vitals;
CREATE TRIGGER trg_abnormal_vitals
    AFTER INSERT ON vitals
    FOR EACH ROW EXECUTE FUNCTION fn_abnormal_vitals_alert();
