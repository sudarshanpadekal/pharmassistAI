# PharmAssist-AI

A full-stack prescription digitization, active-ingredient overlap detection, and multi-pharmacy inventory comparison web application built on a **3NF/BCNF normalized PostgreSQL relational schema**, a **Python FastAPI** backend, and a **React (Vite)** frontend.

---

## Key Features

- **3NF / BCNF Normalized Relational Database:** Designed across 9 normalized tables (`users`, `doctors`, `pharmacies`, `medicines`, `ingredients`, `medicine_ingredients`, `prescriptions`, `prescription_medicines`, `inventory`) to eliminate transitive dependencies and cleanly model many-to-many drug-to-ingredient compositions.
- **AI / NLP Prescription Extraction (`/api/extract`):** Extracts doctor registration numbers, clinical diagnoses, and prescribed medications from unstructured clinical notes or uploaded prescription images using **Google Gemini (`gemini-2.5-flash`)** with a deterministic offline regex fallback, resolving foreign keys directly against PostgreSQL.
- **Atomic Multi-Medicine Transactions (`/api/prescriptions`):** Inserts parent prescription headers and multiple child line items inside a single ACID database transaction (`with conn:`), rolling back completely if any `CHECK` or foreign-key constraint fails.
- **Duplicate Active Ingredient Safety Alerts:** Joins `prescription_medicines` $\rightarrow$ `medicine_ingredients` $\rightarrow$ `ingredients` (`GROUP BY` / `HAVING COUNT(*) > 1`) to automatically flag overlapping active compounds (e.g., prescribing two brands containing *Paracetamol* in the same prescription).
- **Multi-Pharmacy Stock & Cost Comparison (`/api/compare/{prescription_id}`):** Uses relational joins across pharmacies and live inventory to rank pharmacies by item availability and compute estimated total course cost (`unit_price * duration_days`).
- **Database Triggers & Security:** Uses `bcrypt` password hashing, Pydantic request validation, parameterized SQL queries (`%s`), `ON CONFLICT` inventory upserts, and a `BEFORE INSERT OR UPDATE` PostgreSQL trigger (`trg_inventory_updated`) to maintain `last_updated` timestamps automatically.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Database** | PostgreSQL 18 (DDL `CHECK`/`UNIQUE`/`FK` constraints, PL/pgSQL triggers) |
| **Backend** | Python 3, FastAPI, Uvicorn, Pydantic, `psycopg2-binary`, `passlib[bcrypt]`, `google-genai` |
| **Frontend** | React 18, Vite, Bootstrap 5 |

---

## Project Structure

```text
pharmassistAI/
├── .env                        # Database credentials & optional Gemini API key
├── .gitignore
├── README.md
├── database/
│   ├── schema.sql              # 9 normalized tables, constraints, indexes, and triggers
│   └── sample_data.sql         # Seed doctors, pharmacies, medicines, ingredients & stock
├── backend/
│   ├── requirements.txt        # Python dependencies
│   └── main.py                 # FastAPI REST endpoints & SQL transactions
└── frontend/
    ├── index.html              # Root HTML entry point (Bootstrap 5 CDN)
    ├── package.json
    └── src/
        ├── main.jsx
        └── App.jsx             # Authentication & 4-form interactive dashboard