-- Seed Data for PharmAssist-AI

INSERT INTO doctors (doctor_name, specialization, registration_number, phone) VALUES
('Dr. Meera Shenoy', 'General Medicine', 'KMC-45892', '+91-9845012345'),
('Dr. Rajesh Kulkarni', 'Pulmonology', 'KMC-39104', '+91-9845067890'),
('Dr. Ananya Rao', 'Pediatrics', 'KMC-51288', '+91-9845099887')
ON CONFLICT (registration_number) DO NOTHING;

INSERT INTO pharmacies (pharmacy_name, address, phone, email) VALUES
('MedPlus Pharmacy - Jayanagar', '4th Block, Jayanagar, Bengaluru', '080-26631122', 'jayanagar@medplus.in'),
('Apollo Pharmacy - Indiranagar', '100 Feet Rd, Indiranagar, Bengaluru', '080-25214455', 'indiranagar@apollopharmacy.in'),
('Wellness Forever - Koramangala', '5th Block, Koramangala, Bengaluru', '080-41127788', 'koramangala@wellnessforever.in');

INSERT INTO medicines (brand_name, generic_name, dosage_form, strength, manufacturer) VALUES
('Dolo 650', 'Paracetamol', 'Tablet', '650 mg', 'Micro Labs Ltd'),
('Augmentin 625 Duo', 'Amoxicillin + Clavulanic Acid', 'Tablet', '625 mg', 'GSK Pharmaceuticals'),
('Pan-D', 'Pantoprazole + Domperidone', 'Capsule', '40 mg / 30 mg', 'Alkem Laboratories'),
('Crocin Advance', 'Paracetamol', 'Tablet', '500 mg', 'Haleon'),
('Azithral 500', 'Azithromycin', 'Tablet', '500 mg', 'Alembic Pharmaceuticals');

INSERT INTO ingredients (ingredient_name, description) VALUES
('Paracetamol', 'Analgesic and antipyretic used to treat fever and mild-to-moderate pain.'),
('Amoxicillin', 'Penicillin-type broad-spectrum antibiotic.'),
('Clavulanic Acid', 'Beta-lactamase inhibitor that prevents bacterial resistance to amoxicillin.'),
('Pantoprazole', 'Proton pump inhibitor (PPI) that reduces stomach acid production.'),
('Domperidone', 'Prokinetic and antiemetic agent.'),
('Azithromycin', 'Macrolide antibiotic used for respiratory and bacterial infections.')
ON CONFLICT (ingredient_name) DO NOTHING;

-- Map Medicines to Active Ingredients
INSERT INTO medicine_ingredients (medicine_id, ingredient_id, quantity, unit) VALUES
(1, 1, 650.00, 'mg'), -- Dolo 650 -> Paracetamol
(2, 2, 500.00, 'mg'), -- Augmentin 625 -> Amoxicillin
(2, 3, 125.00, 'mg'), -- Augmentin 625 -> Clavulanic Acid
(3, 4, 40.00, 'mg'),  -- Pan-D -> Pantoprazole
(3, 5, 30.00, 'mg'),  -- Pan-D -> Domperidone
(4, 1, 500.00, 'mg'), -- Crocin Advance -> Paracetamol (shares Paracetamol with Dolo 650)
(5, 6, 500.00, 'mg')  -- Azithral 500 -> Azithromycin
ON CONFLICT DO NOTHING;

-- Seed Live Pharmacy Inventory
INSERT INTO inventory (pharmacy_id, medicine_id, quantity_available, unit_price) VALUES
(1, 1, 150, 3.20),
(1, 2, 60, 22.50),
(1, 3, 85, 19.00),
(1, 4, 120, 2.10),
(2, 1, 200, 3.30),
(2, 2, 0, 23.00),   -- Out of stock at Apollo to demonstrate stock comparison
(2, 3, 95, 18.50),
(2, 5, 45, 24.00),
(3, 1, 90, 3.15),
(3, 2, 40, 22.00),
(3, 3, 70, 19.50),
(3, 5, 50, 23.50)
ON CONFLICT (pharmacy_id, medicine_id) DO NOTHING;