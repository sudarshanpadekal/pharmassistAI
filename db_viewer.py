import os
from datetime import date, datetime
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

load_dotenv()

viewer_app = FastAPI(title="PharmAssist-AI — Live PostgreSQL Relation Inspector")

# Ordered logically by dependency (parent entities -> junction/transactional tables)
ORDERED_TABLES = [
    "users",
    "doctors",
    "pharmacies",
    "medicines",
    "ingredients",
    "medicine_ingredients",
    "prescriptions",
    "prescription_medicines",
    "inventory",
]


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


def serialize_val(val):
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    return val


@viewer_app.get("/api/all-relations")
def fetch_all_relations():
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Discover all public base tables
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
            """)
            existing = {r["table_name"] for r in cur.fetchall()}
            tables = [t for t in ORDERED_TABLES if t in existing] + sorted(existing - set(ORDERED_TABLES))

            # Primary key lookup
            cur.execute("""
                SELECT kcu.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'public';
            """)
            pk_map = {}
            for r in cur.fetchall():
                pk_map.setdefault(r["table_name"], set()).add(r["column_name"])

            # Foreign key lookup
            cur.execute("""
                SELECT kcu.table_name,
                       kcu.column_name,
                       ccu.table_name AS ref_table,
                       ccu.column_name AS ref_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                 AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
            """)
            fk_map = {}
            for r in cur.fetchall():
                fk_map.setdefault(r["table_name"], {})[r["column_name"]] = f"{r['ref_table']}.{r['ref_column']}"

            result = []
            for tbl in tables:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position;
                """, (tbl,))
                cols = []
                for c in cur.fetchall():
                    cname = c["column_name"]
                    cols.append({
                        "name": cname,
                        "type": c["data_type"],
                        "nullable": c["is_nullable"] == "YES",
                        "is_pk": cname in pk_map.get(tbl, set()),
                        "fk_target": fk_map.get(tbl, {}).get(cname),
                    })

                pk_cols = [c["name"] for c in cols if c["is_pk"]]
                order_clause = f"ORDER BY {', '.join(pk_cols)}" if pk_cols else ""
                cur.execute(f"SELECT * FROM {tbl} {order_clause};")
                raw_rows = cur.fetchall()

                rows = []
                for row in raw_rows:
                    clean_row = {}
                    for k, v in row.items():
                        clean_row[k] = "•••••••• (bcrypt)" if k == "password_hash" else serialize_val(v)
                    rows.append(clean_row)

                result.append({
                    "table_name": tbl,
                    "columns": cols,
                    "row_count": len(rows),
                    "rows": rows,
                })

            return {
                "database": os.getenv("DB_NAME", "pharmassist"),
                "table_count": len(result),
                "total_rows": sum(t["row_count"] for t in result),
                "relations": result,
            }
    finally:
        conn.close()


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PharmAssist-AI | 3NF/BCNF Database Relations Inspector</title>
  <style>
    :root {
      --bg: #0b0f19;
      --surface: #111827;
      --surface-2: #1f2937;
      --border: #374151;
      --text: #f3f4f6;
      --muted: #9ca3af;
      --accent: #3b82f6;
      --pk: #f59e0b;
      --fk: #10b981;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }
    header {
      position: sticky;
      top: 0;
      z-index: 20;
      background: rgba(17, 24, 39, 0.95);
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--border);
      padding: 14px 24px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .title-group h1 {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      color: #fff;
    }
    .title-group p {
      margin: 2px 0 0;
      font-size: 12px;
      color: var(--muted);
    }
    .controls {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    input[type="search"] {
      background: var(--surface-2);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 7px 12px;
      border-radius: 6px;
      font-size: 13px;
      width: 250px;
    }
    button {
      background: var(--accent);
      color: #fff;
      border: none;
      padding: 7px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }
    button:hover { opacity: 0.9; }
    .jump-bar {
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 10px 24px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .jump-chip {
      text-decoration: none;
      color: var(--text);
      background: var(--surface-2);
      border: 1px solid var(--border);
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    .jump-chip span {
      color: var(--accent);
      font-weight: 700;
      margin-left: 4px;
    }
    main {
      max-width: 1440px;
      margin: 24px auto;
      padding: 0 24px 60px;
      display: flex;
      flex-direction: column;
      gap: 28px;
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
    }
    .card-header {
      padding: 14px 18px;
      background: var(--surface-2);
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
    }
    .tbl-name {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 16px;
      font-weight: 700;
      color: #60a5fa;
    }
    .row-pill {
      background: rgba(59, 130, 246, 0.15);
      color: #93c5fd;
      border: 1px solid rgba(59, 130, 246, 0.35);
      padding: 2px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
    }
    .table-wrap {
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      padding: 10px 14px;
      text-align: left;
      border-bottom: 1px solid #1f2937;
      vertical-align: top;
    }
    th {
      background: #0f172a;
      color: #e5e7eb;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      white-space: nowrap;
    }
    tr:hover td { background: rgba(255, 255, 255, 0.02); }
    .col-meta {
      display: block;
      font-weight: 400;
      font-size: 10px;
      color: var(--muted);
      margin-top: 2px;
    }
    .badge {
      display: inline-block;
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 700;
      margin-right: 4px;
    }
    .badge-pk { background: rgba(245, 158, 11, 0.2); color: var(--pk); border: 1px solid rgba(245, 158, 11, 0.4); }
    .badge-fk { background: rgba(16, 185, 129, 0.15); color: var(--fk); border: 1px solid rgba(16, 185, 129, 0.4); }
    .null-val { color: #6b7280; font-style: italic; }
    .empty { padding: 20px; text-align: center; color: var(--muted); font-size: 13px; }
  </style>
</head>
<body>
  <header>
    <div class="title-group">
      <h1>PharmAssist-AI — PostgreSQL Database Relations</h1>
      <p id="summary">Loading relations from PostgreSQL...</p>
    </div>
    <div class="controls">
      <input type="search" id="filterInput" placeholder="Filter rows or table names..." oninput="renderTables()" />
      <button onclick="loadData()">Refresh Data</button>
    </div>
  </header>

  <nav class="jump-bar" id="jumpBar"></nav>
  <main id="container"></main>

  <script>
    let dbPayload = null;

    async function loadData() {
      const res = await fetch("/api/all-relations");
      dbPayload = await res.json();
      document.getElementById("summary").textContent =
        `Database: ${dbPayload.database} · ${dbPayload.table_count} Relations (3NF/BCNF) · ${dbPayload.total_rows} Total Tuples`;
      renderTables();
    }

    function escapeHtml(val) {
      if (val === null || val === undefined) return '<span class="null-val">NULL</span>';
      return String(val)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    }

    function renderTables() {
      if (!dbPayload) return;
      const q = document.getElementById("filterInput").value.trim().toLowerCase();
      const jumpBar = document.getElementById("jumpBar");
      const container = document.getElementById("container");

      jumpBar.innerHTML = dbPayload.relations
        .map(r => `<a class="jump-chip" href="#tbl-${r.table_name}">${r.table_name}<span>(${r.row_count})</span></a>`)
        .join("");

      container.innerHTML = dbPayload.relations.map(rel => {
        const tableMatches = rel.table_name.toLowerCase().includes(q);
        const filteredRows = !q || tableMatches
          ? rel.rows
          : rel.rows.filter(row => Object.values(row).some(v => String(v ?? "").toLowerCase().includes(q)));

        if (q && !tableMatches && filteredRows.length === 0) return "";

        const headers = rel.columns.map(col => {
          const pkTag = col.is_pk ? `<span class="badge badge-pk">PK</span>` : "";
          const fkTag = col.fk_target ? `<span class="badge badge-fk">FK → ${col.fk_target}</span>` : "";
          return `<th>
            ${pkTag}${col.name}
            <span class="col-meta">${col.type} ${fkTag}</span>
          </th>`;
        }).join("");

        const body = filteredRows.length === 0
          ? `<tr><td colspan="${rel.columns.length}" class="empty">0 tuples in ${rel.table_name}</td></tr>`
          : filteredRows.map(row =>
              `<tr>${rel.columns.map(c => `<td>${escapeHtml(row[c.name])}</td>`).join("")}</tr>`
            ).join("");

        return `
          <section class="card" id="tbl-${rel.table_name}">
            <div class="card-header">
              <div class="tbl-name">${rel.table_name}</div>
              <div class="row-pill">${filteredRows.length} tuple${filteredRows.length === 1 ? "" : "s"}</div>
            </div>
            <div class="table-wrap">
              <table>
                <thead><tr>${headers}</tr></thead>
                <tbody>${body}</tbody>
              </table>
            </div>
          </section>
        `;
      }).join("");
    }

    loadData();
  </script>
</body>
</html>
"""


@viewer_app.get("/", response_class=HTMLResponse)
def serve_viewer():
    return HTML_PAGE