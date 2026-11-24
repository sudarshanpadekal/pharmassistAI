import os
import re
import json
import base64
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PharmAssist-AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url, sslmode="require")
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "pharmassist"),
        user=os.getenv("DB_USER", "pharmassist_user"),
        password=os.getenv("DB_PASSWORD", "user"),
    )

# --- Pydantic Validation Schemas ---
class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone: Optional[str] = Field(None, pattern=r"^\+?[0-9\-]{10,15}$")
    date_of_birth: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class MedicineItem(BaseModel):
    medicine_id: int
    prescribed_dose: str = Field(..., min_length=1)
    frequency: str = Field(..., min_length=1)
    duration_days: int = Field(..., gt=0, le=365)
    instructions: Optional[str] = ""

class PrescriptionCreateRequest(BaseModel):
    user_id: int
    doctor_id: int
    pharmacy_id: Optional[int] = None
    diagnosis: str = Field(..., min_length=2)
    medicines: list[MedicineItem] = Field(..., min_length=1)

class InventoryUpdateRequest(BaseModel):
    pharmacy_id: int
    medicine_id: int
    quantity_available: int = Field(..., ge=0)
    unit_price: float = Field(..., ge=0)

# --- 1. Authentication ---
@app.post("/api/register")
def register_user(payload: RegisterRequest):
    conn = get_db()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO users (full_name, email, password_hash, phone, date_of_birth)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING user_id, full_name, email;
                    """,
                    (
                        payload.full_name.strip(),
                        payload.email.lower(),
                        pwd_context.hash(payload.password),
                        payload.phone,
                        payload.date_of_birth or None,
                    ),
                )
                return {"user": cur.fetchone()}
    except psycopg2.Error as e:
        raise HTTPException(status_code=400, detail=e.pgerror or "Registration failed")
    finally:
        conn.close()

@app.post("/api/login")
def login_user(payload: LoginRequest):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT user_id, full_name, email, password_hash FROM users WHERE email = %s;",
                (payload.email.lower(),),
            )
            user = cur.fetchone()
        if not user or not pwd_context.verify(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        del user["password_hash"]
        return {"user": user}
    finally:
        conn.close()

# --- 2. Dashboard Data & Ingredient Overlap Detection ---
@app.get("/api/dashboard")
def get_dashboard(user_id: Optional[int] = None):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT doctor_id, doctor_name, registration_number, specialization FROM doctors ORDER BY doctor_name;")
            doctors = cur.fetchall()

            cur.execute("SELECT pharmacy_id, pharmacy_name, address FROM pharmacies ORDER BY pharmacy_name;")
            pharmacies = cur.fetchall()

            cur.execute("SELECT medicine_id, brand_name, generic_name, strength FROM medicines ORDER BY brand_name;")
            medicines = cur.fetchall()

            prescriptions = []
            if user_id:
                cur.execute("""
                    SELECT p.prescription_id, p.prescription_date, p.diagnosis, p.status,
                           d.doctor_name, d.registration_number,
                           COALESCE(ph.pharmacy_name, 'Unassigned') AS pharmacy_name
                    FROM prescriptions p
                    JOIN doctors d ON p.doctor_id = d.doctor_id
                    LEFT JOIN pharmacies ph ON p.pharmacy_id = ph.pharmacy_id
                    WHERE p.user_id = %s
                    ORDER BY p.prescription_id DESC;
                """, (user_id,))
                prescriptions = cur.fetchall()

                for rx in prescriptions:
                    cur.execute("""
                        SELECT pm.prescribed_dose, pm.frequency, pm.duration_days, pm.instructions,
                               m.brand_name, m.strength,
                               STRING_AGG(i.ingredient_name || ' (' || mi.quantity || mi.unit || ')', ', ') AS composition
                        FROM prescription_medicines pm
                        JOIN medicines m ON pm.medicine_id = m.medicine_id
                        LEFT JOIN medicine_ingredients mi ON m.medicine_id = mi.medicine_id
                        LEFT JOIN ingredients i ON mi.ingredient_id = i.ingredient_id
                        WHERE pm.prescription_id = %s
                        GROUP BY pm.prescription_medicine_id, m.brand_name, m.strength;
                    """, (rx["prescription_id"],))
                    rx["items"] = cur.fetchall()

                    cur.execute("""
                        SELECT i.ingredient_name, COUNT(*) AS drug_count
                        FROM prescription_medicines pm
                        JOIN medicine_ingredients mi ON pm.medicine_id = mi.medicine_id
                        JOIN ingredients i ON mi.ingredient_id = i.ingredient_id
                        WHERE pm.prescription_id = %s
                        GROUP BY i.ingredient_name
                        HAVING COUNT(*) > 1;
                    """, (rx["prescription_id"],))
                    rx["duplicate_ingredients"] = [row["ingredient_name"] for row in cur.fetchall()]

            cur.execute("""
                SELECT ph.pharmacy_name, ph.address, m.brand_name, m.generic_name,
                       i.quantity_available, i.unit_price, i.last_updated
                FROM inventory i
                JOIN pharmacies ph ON i.pharmacy_id = ph.pharmacy_id
                JOIN medicines m ON i.medicine_id = m.medicine_id
                ORDER BY ph.pharmacy_name, m.brand_name;
            """)
            inventory = cur.fetchall()

        return {
            "doctors": doctors,
            "pharmacies": pharmacies,
            "medicines": medicines,
            "prescriptions": prescriptions,
            "inventory": inventory,
        }
    finally:
        conn.close()

# --- 3. Pharmacy Stock & Price Comparison ---
@app.get("/api/compare/{prescription_id}")
def compare_pharmacies(prescription_id: int):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT ph.pharmacy_id, ph.pharmacy_name, ph.address,
                       COUNT(pm.medicine_id) AS total_rx_items,
                       COUNT(CASE WHEN inv.quantity_available > 0 THEN 1 END) AS in_stock_items,
                       COALESCE(SUM(CASE WHEN inv.quantity_available > 0 THEN inv.unit_price * pm.duration_days ELSE 0 END), 0) AS estimated_total
                FROM pharmacies ph
                CROSS JOIN prescription_medicines pm
                LEFT JOIN inventory inv ON inv.pharmacy_id = ph.pharmacy_id AND inv.medicine_id = pm.medicine_id
                WHERE pm.prescription_id = %s
                GROUP BY ph.pharmacy_id, ph.pharmacy_name, ph.address
                ORDER BY in_stock_items DESC, estimated_total ASC;
            """, (prescription_id,))
            return {"comparison": cur.fetchall()}
    finally:
        conn.close()

# --- 4. AI / NLP Prescription Extraction ---
@app.post("/api/extract")
async def extract_prescription(raw_text: str = Form(""), rx_image: Optional[UploadFile] = File(None)):
    image_bytes = await rx_image.read() if rx_image and rx_image.filename else None
    api_key = os.getenv("GROQ_API_KEY", "").strip()

    parsed = None
    if api_key and api_key != "gsk_your_actual_groq_api_key_here" and (raw_text or image_bytes):
        try:
            from groq import Groq
            client = Groq(api_key=api_key)

            system_prompt = (
                "You are a medical prescription parser. Return ONLY valid JSON with keys: "
                "doctor_name (string), doctor_reg_no (string), diagnosis (string), and medicines "
                "(array of objects with brand_name, prescribed_dose, frequency, duration_days as integer, instructions). "
                "Use empty strings if a field is not mentioned."
            )

            if image_bytes:
                b64_img = base64.b64encode(image_bytes).decode("utf-8")
                mime_type = rx_image.content_type or "image/jpeg"
                user_content = [
                    {"type": "text", "text": raw_text or "Extract the prescription details from this image."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}},
                ]
                model_id = "qwen/qwen3.8-27b"
            else:
                user_content = raw_text
                model_id = "llama-3.3-70b-versatile"

            res = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            parsed = json.loads(res.choices[0].message.content)
        except Exception as e:
            print(f"[Groq Extract Error]: {e}")
            parsed = None

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not parsed:
                reg_match = re.search(r"(KMC-\d+)", raw_text, re.IGNORECASE)
                doc_name_match = re.search(r"Dr\.?\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)", raw_text, re.IGNORECASE)
                diag_match = re.search(r"Diagnosis:\s*([^\n.;]+)", raw_text, re.IGNORECASE)

                cur.execute("SELECT medicine_id, brand_name, generic_name FROM medicines;")
                matched_meds = []
                for m in cur.fetchall():
                    base_brand = m["brand_name"].split()[0]
                    if re.search(rf"\b{re.escape(base_brand)}\b", raw_text, re.IGNORECASE):
                        matched_meds.append({
                            "brand_name": m["brand_name"],
                            "prescribed_dose": "1 tablet",
                            "frequency": "Twice daily",
                            "duration_days": 5,
                            "instructions": "After food",
                            "resolved_medicine_id": m["medicine_id"],
                        })

                parsed = {
                    "doctor_reg_no": reg_match.group(1).upper() if reg_match else "",
                    "doctor_name": doc_name_match.group(1).strip() if doc_name_match else "",
                    "diagnosis": diag_match.group(1).strip() if diag_match else "",
                    "medicines": matched_meds,
                }

            doc = None
            if parsed.get("doctor_reg_no"):
                cur.execute(
                    "SELECT doctor_id FROM doctors WHERE registration_number ILIKE %s LIMIT 1;",
                    (parsed["doctor_reg_no"],),
                )
                doc = cur.fetchone()
            if not doc and parsed.get("doctor_name"):
                clean_name = re.sub(r"^Dr\.?\s*", "", parsed["doctor_name"], flags=re.IGNORECASE).strip()
                cur.execute(
                    "SELECT doctor_id FROM doctors WHERE doctor_name ILIKE %s LIMIT 1;",
                    (f"%{clean_name}%",),
                )
                doc = cur.fetchone()
            parsed["resolved_doctor_id"] = doc["doctor_id"] if doc else ""

            for med in parsed.get("medicines", []):
                if not med.get("resolved_medicine_id"):
                    base_word = med.get("brand_name", "").split()[0] if med.get("brand_name") else ""
                    if base_word:
                        cur.execute(
                            "SELECT medicine_id FROM medicines WHERE brand_name ILIKE %s OR generic_name ILIKE %s LIMIT 1;",
                            (f"%{base_word}%", f"%{base_word}%"),
                        )
                        m = cur.fetchone()
                        med["resolved_medicine_id"] = m["medicine_id"] if m else ""
    finally:
        conn.close()

    return parsed

# --- 5. Atomic Multi-Medicine Prescription Insert ---
@app.post("/api/prescriptions")
def create_prescription(payload: PrescriptionCreateRequest):
    conn = get_db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO prescriptions (user_id, doctor_id, pharmacy_id, diagnosis, status)
                    VALUES (%s, %s, %s, %s, 'verified')
                    RETURNING prescription_id;
                    """,
                    (payload.user_id, payload.doctor_id, payload.pharmacy_id, payload.diagnosis.strip()),
                )
                rx_id = cur.fetchone()[0]

                for item in payload.medicines:
                    cur.execute(
                        """
                        INSERT INTO prescription_medicines
                            (prescription_id, medicine_id, prescribed_dose, frequency, duration_days, instructions)
                        VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                        (rx_id, item.medicine_id, item.prescribed_dose, item.frequency, item.duration_days, item.instructions),
                    )
        return {"message": f"Prescription #{rx_id} verified and saved!", "prescription_id": rx_id}
    except psycopg2.Error as e:
        raise HTTPException(status_code=400, detail=e.pgerror or "Database constraint violation")
    finally:
        conn.close()

# --- 6. Pharmacy Inventory Upsert ---
@app.post("/api/inventory")
def update_inventory(payload: InventoryUpdateRequest):
    conn = get_db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO inventory (pharmacy_id, medicine_id, quantity_available, unit_price)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (pharmacy_id, medicine_id)
                    DO UPDATE SET quantity_available = EXCLUDED.quantity_available, unit_price = EXCLUDED.unit_price;
                    """,
                    (payload.pharmacy_id, payload.medicine_id, payload.quantity_available, payload.unit_price),
                )
        return {"message": "Inventory updated successfully!"}
    except psycopg2.Error as e:
        raise HTTPException(status_code=400, detail=e.pgerror or "Inventory constraint error")
    finally:
        conn.close()