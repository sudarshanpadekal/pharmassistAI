-- PharmAssist-AI: 9-Table Normalized Schema (3NF / BCNF)

CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doctors (
    doctor_id SERIAL PRIMARY KEY,
    doctor_name VARCHAR(100) NOT NULL,
    specialization VARCHAR(100),
    registration_number VARCHAR(50) UNIQUE NOT NULL,
    phone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS pharmacies (
    pharmacy_id SERIAL PRIMARY KEY,
    pharmacy_name VARCHAR(150) NOT NULL,
    address TEXT NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(150)
);

CREATE TABLE IF NOT EXISTS medicines (
    medicine_id SERIAL PRIMARY KEY,
    brand_name VARCHAR(150) NOT NULL,
    generic_name VARCHAR(150) NOT NULL,
    dosage_form VARCHAR(50) NOT NULL,
    strength VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(150)
);

CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id SERIAL PRIMARY KEY,
    ingredient_name VARCHAR(150) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS medicine_ingredients (
    medicine_id INT NOT NULL REFERENCES medicines(medicine_id) ON DELETE CASCADE,
    ingredient_id INT NOT NULL REFERENCES ingredients(ingredient_id) ON DELETE RESTRICT,
    quantity NUMERIC(10, 2) NOT NULL CHECK (quantity > 0),
    unit VARCHAR(20) NOT NULL,
    PRIMARY KEY (medicine_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS prescriptions (
    prescription_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    doctor_id INT NOT NULL REFERENCES doctors(doctor_id) ON DELETE RESTRICT,
    pharmacy_id INT REFERENCES pharmacies(pharmacy_id) ON DELETE SET NULL,
    prescription_date DATE NOT NULL DEFAULT CURRENT_DATE,
    diagnosis TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'rejected'))
);

CREATE TABLE IF NOT EXISTS prescription_medicines (
    prescription_medicine_id SERIAL PRIMARY KEY,
    prescription_id INT NOT NULL REFERENCES prescriptions(prescription_id) ON DELETE CASCADE,
    medicine_id INT NOT NULL REFERENCES medicines(medicine_id) ON DELETE RESTRICT,
    prescribed_dose VARCHAR(50) NOT NULL,
    frequency VARCHAR(50) NOT NULL,
    duration_days INT NOT NULL CHECK (duration_days > 0),
    instructions TEXT
);

CREATE TABLE IF NOT EXISTS inventory (
    inventory_id SERIAL PRIMARY KEY,
    pharmacy_id INT NOT NULL REFERENCES pharmacies(pharmacy_id) ON DELETE CASCADE,
    medicine_id INT NOT NULL REFERENCES medicines(medicine_id) ON DELETE CASCADE,
    quantity_available INT NOT NULL DEFAULT 0 CHECK (quantity_available >= 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (pharmacy_id, medicine_id)
);

-- Trigger Function: Auto-update last_updated timestamp on inventory changes
CREATE OR REPLACE FUNCTION update_inventory_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_inventory_updated ON inventory;
CREATE TRIGGER trg_inventory_updated
BEFORE INSERT OR UPDATE ON inventory
FOR EACH ROW
EXECUTE FUNCTION update_inventory_timestamp();