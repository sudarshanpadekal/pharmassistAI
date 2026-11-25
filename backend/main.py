# import os
# import re
# import json
# import base64
# from typing import Optional
# import psycopg2
# from psycopg2.extras import RealDictCursor
# from fastapi import FastAPI, HTTPException, UploadFile, File, Form
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, EmailStr, Field
# from passlib.context import CryptContext
# from dotenv import load_dotenv

# load_dotenv()

# app = FastAPI(title="PharmAssist-AI API")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def get_db():
#     database_url = os.getenv("DATABASE_URL")
#     if database_url:
#         return psycopg2.connect(database_url, sslmode="require")
#     return psycopg2.connect(
#         host=os.getenv("DB_HOST", "localhost"),
#         port=os.getenv("DB_PORT", "5432"),
#         dbname=os.getenv("DB_NAME", "pharmassist"),
#         user=os.getenv("DB_USER", "pharmassist_user"),
#         password=os.getenv("DB_PASSWORD", "user"),
#     )

# # --- Pydantic Validation Schemas ---
# class RegisterRequest(BaseModel):
#     full_name: str = Field(..., min_length=2, max_length=100)
#     email: EmailStr
#     password: str = Field(..., min_length=8)
#     phone: Optional[str] = Field(None, pattern=r"^\+?[0-9\-]{10,15}$")
#     date_of_birth: Optional[str] = None

# class LoginRequest(BaseModel):
#     email: EmailStr
#     password: str

# class MedicineItem(BaseModel):
#     medicine_id: int
#     prescribed_dose: str = Field(..., min_length=1)
#     frequency: str = Field(..., min_length=1)
#     duration_days: int = Field(..., gt=0, le=365)
#     instructions: Optional[str] = ""

# class PrescriptionCreateRequest(BaseModel):
#     user_id: int
#     doctor_id: int
#     pharmacy_id: Optional[int] = None
#     diagnosis: str = Field(..., min_length=2)
#     medicines: list[MedicineItem] = Field(..., min_length=1)

# class InventoryUpdateRequest(BaseModel):
#     pharmacy_id: int
#     medicine_id: int
#     quantity_available: int = Field(..., ge=0)
#     unit_price: float = Field(..., ge=0)

# # --- 1. Authentication ---
# @app.post("/api/register")
# def register_user(payload: RegisterRequest):
#     conn = get_db()
#     try:
#         with conn:
#             with conn.cursor(cursor_factory=RealDictCursor) as cur:
#                 cur.execute(
#                     """
#                     INSERT INTO users (full_name, email, password_hash, phone, date_of_birth)
#                     VALUES (%s, %s, %s, %s, %s)
#                     RETURNING user_id, full_name, email;
#                     """,
#                     (
#                         payload.full_name.strip(),
#                         payload.email.lower(),
#                         pwd_context.hash(payload.password),
#                         payload.phone,
#                         payload.date_of_birth or None,
#                     ),
#                 )
#                 return {"user": cur.fetchone()}
#     except psycopg2.Error as e:
#         raise HTTPException(status_code=400, detail=e.pgerror or "Registration failed")
#     finally:
#         conn.close()

# @app.post("/api/login")
# def login_user(payload: LoginRequest):
#     conn = get_db()
#     try:
#         with conn.cursor(cursor_factory=RealDictCursor) as cur:
#             cur.execute(
#                 "SELECT user_id, full_name, email, password_hash FROM users WHERE email = %s;",
#                 (payload.email.lower(),),
#             )
#             user = cur.fetchone()
#         if not user or not pwd_context.verify(payload.password, user["password_hash"]):
#             raise HTTPException(status_code=401, detail="Invalid email or password")
#         del user["password_hash"]
#         return {"user": user}
#     finally:
#         conn.close()

# # --- 2. Dashboard Data & Ingredient Overlap Detection ---
# @app.get("/api/dashboard")
# def get_dashboard(user_id: Optional[int] = None):
#     conn = get_db()
#     try:
#         with conn.cursor(cursor_factory=RealDictCursor) as cur:
#             cur.execute("SELECT doctor_id, doctor_name, registration_number, specialization FROM doctors ORDER BY doctor_name;")
#             doctors = cur.fetchall()

#             cur.execute("SELECT pharmacy_id, pharmacy_name, address FROM pharmacies ORDER BY pharmacy_name;")
#             pharmacies = cur.fetchall()

#             cur.execute("SELECT medicine_id, brand_name, generic_name, strength FROM medicines ORDER BY brand_name;")
#             medicines = cur.fetchall()

#             prescriptions = []
#             if user_id:
#                 cur.execute("""
#                     SELECT p.prescription_id, p.prescription_date, p.diagnosis, p.status,
#                            d.doctor_name, d.registration_number,
#                            COALESCE(ph.pharmacy_name, 'Unassigned') AS pharmacy_name
#                     FROM prescriptions p
#                     JOIN doctors d ON p.doctor_id = d.doctor_id
#                     LEFT JOIN pharmacies ph ON p.pharmacy_id = ph.pharmacy_id
#                     WHERE p.user_id = %s
#                     ORDER BY p.prescription_id DESC;
#                 """, (user_id,))
#                 prescriptions = cur.fetchall()

#                 for rx in prescriptions:
#                     cur.execute("""
#                         SELECT pm.prescribed_dose, pm.frequency, pm.duration_days, pm.instructions,
#                                m.brand_name, m.strength,
#                                STRING_AGG(i.ingredient_name || ' (' || mi.quantity || mi.unit || ')', ', ') AS composition
#                         FROM prescription_medicines pm
#                         JOIN medicines m ON pm.medicine_id = m.medicine_id
#                         LEFT JOIN medicine_ingredients mi ON m.medicine_id = mi.medicine_id
#                         LEFT JOIN ingredients i ON mi.ingredient_id = i.ingredient_id
#                         WHERE pm.prescription_id = %s
#                         GROUP BY pm.prescription_medicine_id, m.brand_name, m.strength;
#                     """, (rx["prescription_id"],))
#                     rx["items"] = cur.fetchall()

#                     cur.execute("""
#                         SELECT i.ingredient_name, COUNT(*) AS drug_count
#                         FROM prescription_medicines pm
#                         JOIN medicine_ingredients mi ON pm.medicine_id = mi.medicine_id
#                         JOIN ingredients i ON mi.ingredient_id = i.ingredient_id
#                         WHERE pm.prescription_id = %s
#                         GROUP BY i.ingredient_name
#                         HAVING COUNT(*) > 1;
#                     """, (rx["prescription_id"],))
#                     rx["duplicate_ingredients"] = [row["ingredient_name"] for row in cur.fetchall()]

#             cur.execute("""
#                 SELECT ph.pharmacy_name, ph.address, m.brand_name, m.generic_name,
#                        i.quantity_available, i.unit_price, i.last_updated
#                 FROM inventory i
#                 JOIN pharmacies ph ON i.pharmacy_id = ph.pharmacy_id
#                 JOIN medicines m ON i.medicine_id = m.medicine_id
#                 ORDER BY ph.pharmacy_name, m.brand_name;
#             """)
#             inventory = cur.fetchall()

#         return {
#             "doctors": doctors,
#             "pharmacies": pharmacies,
#             "medicines": medicines,
#             "prescriptions": prescriptions,
#             "inventory": inventory,
#         }
#     finally:
#         conn.close()

# # --- 3. Pharmacy Stock & Price Comparison ---
# @app.get("/api/compare/{prescription_id}")
# def compare_pharmacies(prescription_id: int):
#     conn = get_db()
#     try:
#         with conn.cursor(cursor_factory=RealDictCursor) as cur:
#             cur.execute("""
#                 SELECT ph.pharmacy_id, ph.pharmacy_name, ph.address,
#                        COUNT(pm.medicine_id) AS total_rx_items,
#                        COUNT(CASE WHEN inv.quantity_available > 0 THEN 1 END) AS in_stock_items,
#                        COALESCE(SUM(CASE WHEN inv.quantity_available > 0 THEN inv.unit_price * pm.duration_days ELSE 0 END), 0) AS estimated_total
#                 FROM pharmacies ph
#                 CROSS JOIN prescription_medicines pm
#                 LEFT JOIN inventory inv ON inv.pharmacy_id = ph.pharmacy_id AND inv.medicine_id = pm.medicine_id
#                 WHERE pm.prescription_id = %s
#                 GROUP BY ph.pharmacy_id, ph.pharmacy_name, ph.address
#                 ORDER BY in_stock_items DESC, estimated_total ASC;
#             """, (prescription_id,))
#             return {"comparison": cur.fetchall()}
#     finally:
#         conn.close()

# # --- 4. AI / NLP Prescription Extraction ---
# @app.post("/api/extract")
# async def extract_prescription(raw_text: str = Form(""), rx_image: Optional[UploadFile] = File(None)):
#     image_bytes = await rx_image.read() if rx_image and rx_image.filename else None
#     api_key = os.getenv("GROQ_API_KEY", "").strip()

#     parsed = None
#     if api_key and api_key != "gsk_your_actual_groq_api_key_here" and (raw_text or image_bytes):
#         try:
#             from groq import Groq
#             client = Groq(api_key=api_key)

#             system_prompt = (
#                 "You are a medical prescription parser. Return ONLY valid JSON with keys: "
#                 "doctor_name (string), doctor_reg_no (string), diagnosis (string), and medicines "
#                 "(array of objects with brand_name, prescribed_dose, frequency, duration_days as integer, instructions). "
#                 "Use empty strings if a field is not mentioned."
#             )

#             if image_bytes:
#                 b64_img = base64.b64encode(image_bytes).decode("utf-8")
#                 mime_type = rx_image.content_type or "image/jpeg"
#                 user_content = [
#                     {"type": "text", "text": raw_text or "Extract the prescription details from this image."},
#                     {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}},
#                 ]
#                 model_id = "qwen/qwen3.8-27b"
#             else:
#                 user_content = raw_text
#                 model_id = "llama-3.3-70b-versatile"

#             res = client.chat.completions.create(
#                 model=model_id,
#                 messages=[
#                     {"role": "system", "content": system_prompt},
#                     {"role": "user", "content": user_content},
#                 ],
#                 response_format={"type": "json_object"},
#                 temperature=0,
#             )
#             parsed = json.loads(res.choices[0].message.content)
#         except Exception as e:
#             print(f"[Groq Extract Error]: {e}")
#             parsed = None

#     conn = get_db()
#     try:
#         with conn.cursor(cursor_factory=RealDictCursor) as cur:
#             if not parsed:
#                 reg_match = re.search(r"(KMC-\d+)", raw_text, re.IGNORECASE)
#                 doc_name_match = re.search(r"Dr\.?\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)", raw_text, re.IGNORECASE)
#                 diag_match = re.search(r"Diagnosis:\s*([^\n.;]+)", raw_text, re.IGNORECASE)

#                 cur.execute("SELECT medicine_id, brand_name, generic_name FROM medicines;")
#                 matched_meds = []
#                 for m in cur.fetchall():
#                     base_brand = m["brand_name"].split()[0]
#                     if re.search(rf"\b{re.escape(base_brand)}\b", raw_text, re.IGNORECASE):
#                         matched_meds.append({
#                             "brand_name": m["brand_name"],
#                             "prescribed_dose": "1 tablet",
#                             "frequency": "Twice daily",
#                             "duration_days": 5,
#                             "instructions": "After food",
#                             "resolved_medicine_id": m["medicine_id"],
#                         })

#                 parsed = {
#                     "doctor_reg_no": reg_match.group(1).upper() if reg_match else "",
#                     "doctor_name": doc_name_match.group(1).strip() if doc_name_match else "",
#                     "diagnosis": diag_match.group(1).strip() if diag_match else "",
#                     "medicines": matched_meds,
#                 }

#             doc = None
#             if parsed.get("doctor_reg_no"):
#                 cur.execute(
#                     "SELECT doctor_id FROM doctors WHERE registration_number ILIKE %s LIMIT 1;",
#                     (parsed["doctor_reg_no"],),
#                 )
#                 doc = cur.fetchone()
#             if not doc and parsed.get("doctor_name"):
#                 clean_name = re.sub(r"^Dr\.?\s*", "", parsed["doctor_name"], flags=re.IGNORECASE).strip()
#                 cur.execute(
#                     "SELECT doctor_id FROM doctors WHERE doctor_name ILIKE %s LIMIT 1;",
#                     (f"%{clean_name}%",),
#                 )
#                 doc = cur.fetchone()
#             parsed["resolved_doctor_id"] = doc["doctor_id"] if doc else ""

#             for med in parsed.get("medicines", []):
#                 if not med.get("resolved_medicine_id"):
#                     base_word = med.get("brand_name", "").split()[0] if med.get("brand_name") else ""
#                     if base_word:
#                         cur.execute(
#                             "SELECT medicine_id FROM medicines WHERE brand_name ILIKE %s OR generic_name ILIKE %s LIMIT 1;",
#                             (f"%{base_word}%", f"%{base_word}%"),
#                         )
#                         m = cur.fetchone()
#                         med["resolved_medicine_id"] = m["medicine_id"] if m else ""
#     finally:
#         conn.close()

#     return parsed

# # --- 5. Atomic Multi-Medicine Prescription Insert ---
# @app.post("/api/prescriptions")
# def create_prescription(payload: PrescriptionCreateRequest):
#     conn = get_db()
#     try:
#         with conn:
#             with conn.cursor() as cur:
#                 cur.execute(
#                     """
#                     INSERT INTO prescriptions (user_id, doctor_id, pharmacy_id, diagnosis, status)
#                     VALUES (%s, %s, %s, %s, 'verified')
#                     RETURNING prescription_id;
#                     """,
#                     (payload.user_id, payload.doctor_id, payload.pharmacy_id, payload.diagnosis.strip()),
#                 )
#                 rx_id = cur.fetchone()[0]

#                 for item in payload.medicines:
#                     cur.execute(
#                         """
#                         INSERT INTO prescription_medicines
#                             (prescription_id, medicine_id, prescribed_dose, frequency, duration_days, instructions)
#                         VALUES (%s, %s, %s, %s, %s, %s);
#                         """,
#                         (rx_id, item.medicine_id, item.prescribed_dose, item.frequency, item.duration_days, item.instructions),
#                     )
#         return {"message": f"Prescription #{rx_id} verified and saved!", "prescription_id": rx_id}
#     except psycopg2.Error as e:
#         raise HTTPException(status_code=400, detail=e.pgerror or "Database constraint violation")
#     finally:
#         conn.close()

# # --- 6. Pharmacy Inventory Upsert ---
# @app.post("/api/inventory")
# def update_inventory(payload: InventoryUpdateRequest):
#     conn = get_db()
#     try:
#         with conn:
#             with conn.cursor() as cur:
#                 cur.execute(
#                     """
#                     INSERT INTO inventory (pharmacy_id, medicine_id, quantity_available, unit_price)
#                     VALUES (%s, %s, %s, %s)
#                     ON CONFLICT (pharmacy_id, medicine_id)
#                     DO UPDATE SET quantity_available = EXCLUDED.quantity_available, unit_price = EXCLUDED.unit_price;
#                     """,
#                     (payload.pharmacy_id, payload.medicine_id, payload.quantity_available, payload.unit_price),
#                 )
#         return {"message": "Inventory updated successfully!"}
#     except psycopg2.Error as e:
#         raise HTTPException(status_code=400, detail=e.pgerror or "Inventory constraint error")
#     finally:
#         conn.close()
import os
import re
import json
import base64
from pathlib import Path
from typing import Optional, Literal
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PharmAssist-AI Dispensing Portal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

BASE_DIR = Path(__file__).resolve().parent
ROLE_BINDINGS_FILE = BASE_DIR / "role_bindings.json"
PENDING_DOCTORS_FILE = BASE_DIR / "pending_doctors.json"
PENDING_PHARMACISTS_FILE = BASE_DIR / "pending_pharmacists.json"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@pharmassist.in").strip().lower()

# PHARMACY_MANAGERS: maps pharmacy_id (int) -> manager_email (str)
# Set via env as comma-separated "1:manager1@example.com,2:manager2@example.com"
def _load_pharmacy_managers() -> dict:
    raw = os.getenv("PHARMACY_MANAGERS", "").strip()
    result = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if ":" in entry:
            pid_str, email = entry.split(":", 1)
            try:
                result[int(pid_str.strip())] = email.strip().lower()
            except ValueError:
                pass
    return result

PHARMACY_MANAGERS: dict = _load_pharmacy_managers()  # {pharmacy_id -> manager_email}


def load_json_file(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json_file(path: Path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


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


# --- Pydantic Schemas ---
class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone: Optional[str] = Field(None, pattern=r"^\+?[0-9\-]{10,15}$")
    role: Literal["pharmacist", "doctor", "admin"] = "pharmacist"
    pharmacy_id: Optional[int] = None
    registration_number: Optional[str] = None
    specialization: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class WalkInPatientRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^\+?[0-9\-]{10,15}$")
    date_of_birth: Optional[str] = None


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
    requester_role: str
    requester_pharmacy_id: Optional[int] = None
    pharmacy_id: int
    medicine_id: int
    quantity_available: int = Field(..., ge=0)
    unit_price: float = Field(..., ge=0)


# --- 1. Reference Metadata ---
@app.get("/api/meta")
def get_meta():
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT pharmacy_id, pharmacy_name, address FROM pharmacies ORDER BY pharmacy_name;")
            pharmacies = cur.fetchall()
        return {"pharmacies": pharmacies, "admin_email": ADMIN_EMAIL}
    finally:
        conn.close()


# --- 2. Role-Based Registration & Login (Zero Schema Change) ---
@app.post("/api/register")
def register_user(payload: RegisterRequest):
    email = payload.email.lower().strip()

    if payload.role == "admin" and email != ADMIN_EMAIL:
        raise HTTPException(
            status_code=403,
            detail=f"Admin registration is restricted to the configured system admin email ({ADMIN_EMAIL}).",
        )
    if payload.role == "pharmacist" and not payload.pharmacy_id:
        raise HTTPException(status_code=400, detail="Pharmacists must select their assigned pharmacy branch.")
    if payload.role == "doctor" and (not payload.registration_number or not payload.specialization):
        raise HTTPException(status_code=400, detail="Doctors must enter their registration number and specialization.")

    conn = get_db()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if payload.role == "doctor":
                    reg_no = payload.registration_number.strip().upper()
                    cur.execute("SELECT 1 FROM doctors WHERE registration_number ILIKE %s;", (reg_no,))
                    if cur.fetchone():
                        raise HTTPException(status_code=400, detail="This medical registration number is already registered.")

                cur.execute(
                    """
                    INSERT INTO users (full_name, email, password_hash, phone)
                    VALUES (%s, %s, %s, %s)
                    RETURNING user_id, full_name, email;
                    """,
                    (
                        payload.full_name.strip(),
                        email,
                        pwd_context.hash(payload.password),
                        payload.phone,
                    ),
                )
                new_user = dict(cur.fetchone())

        bindings = load_json_file(ROLE_BINDINGS_FILE, {})

        if payload.role == "admin":
            bindings[email] = {"role": "admin"}
            save_json_file(ROLE_BINDINGS_FILE, bindings)
            new_user["role"] = "admin"
            return {"pending": False, "user": new_user}

        if payload.role == "pharmacist":
            pid = int(payload.pharmacy_id)
            # Stage pharmacist registration for Branch Manager approval
            pending_ph = load_json_file(PENDING_PHARMACISTS_FILE, [])
            pending_ph = [p for p in pending_ph if p["email"] != email]
            pending_ph.append({
                "user_id": new_user["user_id"],
                "full_name": new_user["full_name"],
                "email": email,
                "phone": payload.phone or "",
                "pharmacy_id": pid,
            })
            save_json_file(PENDING_PHARMACISTS_FILE, pending_ph)
            bindings[email] = {"role": "pharmacist", "status": "pending", "pharmacy_id": pid}
            save_json_file(ROLE_BINDINGS_FILE, bindings)
            return {
                "pending": True,
                "message": "Pharmacist registration submitted! The Pharmacy Branch Manager must approve your credentials before you can log in.",
            }

        # Doctor self-registration -> stage in pending_doctors.json until System Admin approves
        pending_list = load_json_file(PENDING_DOCTORS_FILE, [])
        pending_list = [p for p in pending_list if p["email"] != email]
        pending_list.append({
            "user_id": new_user["user_id"],
            "full_name": new_user["full_name"],
            "email": email,
            "phone": payload.phone or "",
            "registration_number": payload.registration_number.strip().upper(),
            "specialization": payload.specialization.strip(),
        })
        save_json_file(PENDING_DOCTORS_FILE, pending_list)
        bindings[email] = {"role": "doctor", "status": "pending"}
        save_json_file(ROLE_BINDINGS_FILE, bindings)

        return {
            "pending": True,
            "message": "Doctor application submitted! A System Admin must approve your credentials before it is added to the database.",
        }
    except psycopg2.Error as e:
        raise HTTPException(status_code=400, detail=e.pgerror or "Registration failed (email may already exist).")
    finally:
        conn.close()


@app.post("/api/login")
def login_user(payload: LoginRequest):
    email = payload.email.lower().strip()
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT user_id, full_name, email, password_hash FROM users WHERE email = %s;",
                (email,),
            )
            user = cur.fetchone()
            if not user or not pwd_context.verify(payload.password, user["password_hash"]):
                raise HTTPException(status_code=401, detail="Invalid email or password.")

            bindings = load_json_file(ROLE_BINDINGS_FILE, {})
            role_info = bindings.get(email)

            if email == ADMIN_EMAIL:
                role_info = {"role": "admin"}

            if not role_info:
                raise HTTPException(
                    status_code=403,
                    detail="Access Denied: Patient accounts must use the Patient Companion App to track prescription history.",
                )

            if role_info.get("role") == "doctor":
                if role_info.get("status") == "pending":
                    raise HTTPException(status_code=403, detail="Your doctor registration is awaiting System Admin approval.")
                if role_info.get("status") == "rejected":
                    raise HTTPException(status_code=403, detail="Your doctor registration was rejected by the System Admin.")

                # Confirm doctor exists in the verified PostgreSQL doctors table
                cur.execute(
                    "SELECT doctor_id, doctor_name, registration_number FROM doctors WHERE doctor_id = %s;",
                    (role_info.get("doctor_id"),),
                )
                doc_row = cur.fetchone()
                if not doc_row:
                    raise HTTPException(status_code=403, detail="Verified doctor profile not found in database.")
                role_info["doctor_name"] = doc_row["doctor_name"]

            if role_info.get("role") == "pharmacist":
                if role_info.get("status") == "pending":
                    raise HTTPException(status_code=403, detail="Your pharmacist registration is awaiting Branch Manager approval.")
                if role_info.get("status") == "rejected":
                    raise HTTPException(status_code=403, detail="Your pharmacist registration was rejected by the Branch Manager.")

                cur.execute(
                    "SELECT pharmacy_name FROM pharmacies WHERE pharmacy_id = %s;",
                    (role_info.get("pharmacy_id"),),
                )
                ph_row = cur.fetchone()
                role_info["pharmacy_name"] = ph_row["pharmacy_name"] if ph_row else ""

                # Elevate to pharmacy_manager role if this pharmacist is a configured branch manager
                if PHARMACY_MANAGERS.get(role_info.get("pharmacy_id")) == email:
                    role_info["role"] = "pharmacy_manager"

            del user["password_hash"]
            user_data = {**dict(user), **role_info}
            return {"user": user_data}
    finally:
        conn.close()


# --- 3. Walk-In Patient Registration by Pharmacist ---
@app.post("/api/patients")
def create_walkin_patient(payload: WalkInPatientRequest):
    conn = get_db()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO users (full_name, email, password_hash, phone, date_of_birth)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING user_id, full_name, email, phone;
                    """,
                    (
                        payload.full_name.strip(),
                        payload.email.lower().strip(),
                        pwd_context.hash("PatientPortal@123"),
                        payload.phone,
                        payload.date_of_birth or None,
                    ),
                )
                return {"patient": cur.fetchone()}
    except psycopg2.Error as e:
        raise HTTPException(status_code=400, detail=e.pgerror or "Could not create walk-in patient record.")
    finally:
        conn.close()


# --- 4. System Admin Doctor Approval Workflow ---
@app.get("/api/admin/pending-doctors")
def list_pending_doctors(requester_role: str):
    if requester_role != "admin":
        raise HTTPException(status_code=403, detail="System Admin privileges required.")
    return {"pending_doctors": load_json_file(PENDING_DOCTORS_FILE, [])}


@app.post("/api/admin/doctors/{user_id}/decision")
def decide_doctor(user_id: int, action: Literal["approve", "reject"], requester_role: str):
    if requester_role != "admin":
        raise HTTPException(status_code=403, detail="System Admin privileges required.")

    pending_list = load_json_file(PENDING_DOCTORS_FILE, [])
    target = next((p for p in pending_list if p["user_id"] == user_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Pending doctor application not found.")

    bindings = load_json_file(ROLE_BINDINGS_FILE, {})

    if action == "approve":
        conn = get_db()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO doctors (doctor_name, registration_number, specialization)
                        VALUES (%s, %s, %s)
                        RETURNING doctor_id;
                        """,
                        (target["full_name"], target["registration_number"], target["specialization"]),
                    )
                    new_doctor_id = cur.fetchone()[0]
        except psycopg2.Error as e:
            raise HTTPException(status_code=400, detail=e.pgerror or "Failed to insert doctor into database.")
        finally:
            conn.close()

        bindings[target["email"]] = {
            "role": "doctor",
            "status": "approved",
            "doctor_id": new_doctor_id,
        }
        save_json_file(ROLE_BINDINGS_FILE, bindings)
        save_json_file(PENDING_DOCTORS_FILE, [p for p in pending_list if p["user_id"] != user_id])
        return {"message": f"Approved {target['full_name']} ({target['registration_number']}) and stored in PostgreSQL doctors table!"}

    bindings[target["email"]] = {"role": "doctor", "status": "rejected"}
    save_json_file(ROLE_BINDINGS_FILE, bindings)
    save_json_file(PENDING_DOCTORS_FILE, [p for p in pending_list if p["user_id"] != user_id])
    return {"message": f"Rejected application for {target['full_name']}."}


# --- 5. Role-Scoped Dashboard ---
@app.get("/api/dashboard")
def get_dashboard(
    role: str = "pharmacist",
    pharmacy_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
):
    bindings = load_json_file(ROLE_BINDINGS_FILE, {})
    staff_emails = set(bindings.keys()) | {ADMIN_EMAIL}

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT doctor_id, doctor_name, registration_number, specialization FROM doctors ORDER BY doctor_name;")
            doctors = cur.fetchall()

            cur.execute("SELECT pharmacy_id, pharmacy_name, address FROM pharmacies ORDER BY pharmacy_name;")
            pharmacies = cur.fetchall()

            cur.execute("SELECT medicine_id, brand_name, generic_name, strength FROM medicines ORDER BY brand_name;")
            medicines = cur.fetchall()

            # Exclude pharmacist/doctor/admin portal accounts so only patient customers appear in dropdown
            cur.execute("SELECT user_id, full_name, email, phone FROM users ORDER BY full_name;")
            patients = [u for u in cur.fetchall() if u["email"].lower() not in staff_emails]

            if role == "pharmacist" and pharmacy_id:
                cur.execute("""
                    SELECT p.prescription_id, p.prescription_date, p.diagnosis, p.status,
                           u.full_name AS patient_name, u.phone AS patient_phone,
                           d.doctor_name, d.registration_number,
                           ph.pharmacy_name
                    FROM prescriptions p
                    JOIN users u ON p.user_id = u.user_id
                    JOIN doctors d ON p.doctor_id = d.doctor_id
                    JOIN pharmacies ph ON p.pharmacy_id = ph.pharmacy_id
                    WHERE p.pharmacy_id = %s
                    ORDER BY p.prescription_id DESC;
                """, (pharmacy_id,))
            elif role == "doctor" and doctor_id:
                cur.execute("""
                    SELECT p.prescription_id, p.prescription_date, p.diagnosis, p.status,
                           u.full_name AS patient_name, u.phone AS patient_phone,
                           d.doctor_name, d.registration_number,
                           COALESCE(ph.pharmacy_name, 'Unassigned') AS pharmacy_name
                    FROM prescriptions p
                    JOIN users u ON p.user_id = u.user_id
                    JOIN doctors d ON p.doctor_id = d.doctor_id
                    LEFT JOIN pharmacies ph ON p.pharmacy_id = ph.pharmacy_id
                    WHERE p.doctor_id = %s
                    ORDER BY p.prescription_id DESC;
                """, (doctor_id,))
            else:
                cur.execute("""
                    SELECT p.prescription_id, p.prescription_date, p.diagnosis, p.status,
                           u.full_name AS patient_name, u.phone AS patient_phone,
                           d.doctor_name, d.registration_number,
                           COALESCE(ph.pharmacy_name, 'Unassigned') AS pharmacy_name
                    FROM prescriptions p
                    JOIN users u ON p.user_id = u.user_id
                    JOIN doctors d ON p.doctor_id = d.doctor_id
                    LEFT JOIN pharmacies ph ON p.pharmacy_id = ph.pharmacy_id
                    ORDER BY p.prescription_id DESC;
                """)

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
                SELECT i.pharmacy_id, ph.pharmacy_name, ph.address, m.brand_name, m.generic_name,
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
            "patients": patients,
            "prescriptions": prescriptions,
            "inventory": inventory,
        }
    finally:
        conn.close()


# --- 6. Groq AI / NLP Prescription Extraction ---
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


# --- 7. Atomic Prescription Creation & Dispensing ---
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
        return {"message": f"Prescription #{rx_id} verified and stored!", "prescription_id": rx_id}
    except psycopg2.Error as e:
        raise HTTPException(status_code=400, detail=e.pgerror or "Database constraint violation")
    finally:
        conn.close()


@app.patch("/api/prescriptions/{prescription_id}/dispense")
def dispense_prescription(prescription_id: int, pharmacy_id: int):
    conn = get_db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE prescriptions
                    SET status = 'dispensed'
                    WHERE prescription_id = %s AND pharmacy_id = %s
                    RETURNING prescription_id;
                    """,
                    (prescription_id, pharmacy_id),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=403, detail="Unauthorized: Prescription belongs to a different branch.")
        return {"message": f"Prescription #{prescription_id} issued & marked as dispensed!"}
    finally:
        conn.close()


# --- 8. Branch-Locked Inventory Upsert ---
@app.post("/api/inventory")
def update_inventory(payload: InventoryUpdateRequest):
    if payload.requester_role != "pharmacist" or payload.requester_pharmacy_id != payload.pharmacy_id:
        raise HTTPException(status_code=403, detail="Unauthorized: You can only update stock for your assigned pharmacy branch.")

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
        return {"message": "Branch inventory updated successfully!"}
    except psycopg2.Error as e:
        raise HTTPException(status_code=400, detail=e.pgerror or "Inventory constraint error")
    finally:
        conn.close()


# --- 9. Pharmacy Branch Manager — Pharmacist Approval Workflow ---
@app.get("/api/branch/pending-pharmacists")
def list_pending_pharmacists(requester_role: str, requester_pharmacy_id: int):
    """Returns pharmacist registrations pending approval for the requesting branch manager's pharmacy."""
    if requester_role not in ("pharmacist", "pharmacy_manager"):
        raise HTTPException(status_code=403, detail="Branch Manager privileges required.")
    pending_all = load_json_file(PENDING_PHARMACISTS_FILE, [])
    # Filter to only the manager's branch
    pending_branch = [p for p in pending_all if p["pharmacy_id"] == requester_pharmacy_id]
    return {"pending_pharmacists": pending_branch}


@app.post("/api/branch/pharmacists/{user_id}/decision")
def decide_pharmacist(
    user_id: int,
    action: Literal["approve", "reject"],
    requester_role: str,
    requester_pharmacy_id: int,
):
    """Approve or reject a pending pharmacist registration for the branch manager's pharmacy."""
    if requester_role not in ("pharmacist", "pharmacy_manager"):
        raise HTTPException(status_code=403, detail="Branch Manager privileges required.")

    pending_list = load_json_file(PENDING_PHARMACISTS_FILE, [])
    target = next((p for p in pending_list if p["user_id"] == user_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Pending pharmacist application not found.")
    if target["pharmacy_id"] != requester_pharmacy_id:
        raise HTTPException(status_code=403, detail="Unauthorized: This pharmacist applied for a different branch.")

    bindings = load_json_file(ROLE_BINDINGS_FILE, {})

    if action == "approve":
        bindings[target["email"]] = {
            "role": "pharmacist",
            "status": "approved",
            "pharmacy_id": target["pharmacy_id"],
        }
        save_json_file(ROLE_BINDINGS_FILE, bindings)
        save_json_file(PENDING_PHARMACISTS_FILE, [p for p in pending_list if p["user_id"] != user_id])
        return {"message": f"Approved pharmacist {target['full_name']} for pharmacy branch #{target['pharmacy_id']}!"}

    bindings[target["email"]] = {"role": "pharmacist", "status": "rejected", "pharmacy_id": target["pharmacy_id"]}
    save_json_file(ROLE_BINDINGS_FILE, bindings)
    save_json_file(PENDING_PHARMACISTS_FILE, [p for p in pending_list if p["user_id"] != user_id])
    return {"message": f"Rejected pharmacist application for {target['full_name']}."}