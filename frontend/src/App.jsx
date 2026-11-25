import { useState, useEffect, useCallback } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/* ── tiny helpers ───────────────────────────────────────────── */
const alertMeta = {
  success: { icon: "bi-check-circle-fill", cls: "pa-alert-success" },
  danger:  { icon: "bi-exclamation-triangle-fill", cls: "pa-alert-danger" },
  warning: { icon: "bi-exclamation-circle-fill", cls: "pa-alert-warning" },
  info:    { icon: "bi-info-circle-fill", cls: "pa-alert-info" },
};

function Alert({ alert, onDismiss }) {
  if (!alert) return null;
  const { icon, cls } = alertMeta[alert.type] || alertMeta.info;
  return (
    <div className={`pa-alert ${cls}`} style={{ marginBottom: 20 }}>
      <i className={`bi ${icon} pa-alert-icon`} />
      <span className="pa-alert-text">{alert.text}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{
            background: "none", border: "none", cursor: "pointer",
            color: "inherit", opacity: 0.6, fontSize: 14, padding: "0 0 0 8px",
          }}
        >
          <i className="bi bi-x-lg" />
        </button>
      )}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    verified:  { cls: "pa-badge-blue",  icon: "bi-shield-check", label: "Verified" },
    dispensed: { cls: "pa-badge-green", icon: "bi-bag-check",    label: "Dispensed" },
    pending:   { cls: "pa-badge-amber", icon: "bi-clock",         label: "Pending" },
  };
  const cfg = map[status] || { cls: "pa-badge-muted", icon: "bi-dash", label: status };
  return (
    <span className={`pa-badge ${cfg.cls}`}>
      <i className={`bi ${cfg.icon}`} style={{ fontSize: 10 }} />
      {cfg.label}
    </span>
  );
}

/* ═══════════════════════════════════════════════════════════════
   AUTH PAGE
   ═══════════════════════════════════════════════════════════════ */
function AuthPage({ onLogin, alert, setAlert }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    full_name: "", email: "", password: "", phone: "",
    role: "pharmacist", pharmacy_id: "", registration_number: "", specialization: "",
  });
  const [meta, setMeta] = useState({ pharmacies: [], admin_email: "admin@pharmassist.in" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/meta`).then(r => r.json()).then(setMeta).catch(() => {});
  }, []);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setAlert(null);
    const endpoint = mode === "login" ? "/api/login" : "/api/register";
    const payload = mode === "login"
      ? { email: form.email, password: form.password }
      : {
          full_name: form.full_name, email: form.email, password: form.password,
          phone: form.phone || null, role: form.role,
          pharmacy_id: form.role === "pharmacist" ? Number(form.pharmacy_id) : null,
          registration_number: form.role === "doctor" ? form.registration_number : null,
          specialization: form.role === "doctor" ? form.specialization : null,
        };

    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const json = await res.json();
    setLoading(false);

    if (!res.ok) {
      setAlert({ type: "danger", text: Array.isArray(json.detail) ? json.detail[0].msg : json.detail });
      return;
    }
    if (json.pending) {
      setMode("login");
      setAlert({ type: "warning", text: json.message });
      return;
    }
    onLogin(json.user);
  };

  const roleIcon = {
    pharmacist: "bi-capsule",
    doctor: "bi-heart-pulse",
    admin: "bi-shield-lock",
  };

  return (
    <div className="auth-page">
      {/* Left branding panel */}
      <div className="auth-brand">
        <div className="auth-brand-logo">
          <div className="auth-brand-icon">💊</div>
          <div>
            <div className="auth-brand-name">PharmAssist AI</div>
            <div className="auth-brand-tagline">Dispensing Portal</div>
          </div>
        </div>

        <h1 className="auth-brand-headline">
          Clinical workflows,<br />
          <span>AI-powered.</span>
        </h1>
        <p className="auth-brand-sub">
          A role-based pharmacy management platform combining Groq AI prescription extraction,
          3NF-normalised PostgreSQL records, and real-time duplicate ingredient detection.
        </p>

        <div className="auth-features">
          {[
            { dot: "#3b82f6", text: "Groq LLM prescription OCR & NLP extraction" },
            { dot: "#10b981", text: "Automatic duplicate active-ingredient alerts" },
            { dot: "#8b5cf6", text: "Full RBAC: Admin → Manager → Pharmacist → Doctor" },
            { dot: "#f59e0b", text: "Branch-locked inventory & dispensing controls" },
          ].map((f, i) => (
            <div key={i} className="auth-feature-item">
              <div className="auth-feature-dot" style={{ background: f.dot }} />
              {f.text}
            </div>
          ))}
        </div>
      </div>

      {/* Right form panel */}
      <div className="auth-panel">
        <div className="auth-panel-title">
          {mode === "login" ? "Welcome back" : "Create account"}
        </div>
        <div className="auth-panel-sub">
          {mode === "login"
            ? "Sign in to your dispensing portal account"
            : "Register as staff, pharmacist, or doctor"}
        </div>

        <div className="pa-tabs">
          <button className={`pa-tab ${mode === "login" ? "active" : ""}`}
            onClick={() => { setMode("login"); setAlert(null); }}>
            <i className="bi bi-box-arrow-in-right" /> Sign In
          </button>
          <button className={`pa-tab ${mode === "register" ? "active" : ""}`}
            onClick={() => { setMode("register"); setAlert(null); }}>
            <i className="bi bi-person-plus" /> Register
          </button>
        </div>

        <Alert alert={alert} onDismiss={() => setAlert(null)} />

        <form onSubmit={handleSubmit}>
          {mode === "register" && (
            <>
              {/* Role selector */}
              <div className="pa-field">
                <label className="pa-label">Role</label>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                  {["pharmacist", "doctor", "admin"].map(r => (
                    <button
                      key={r} type="button"
                      onClick={() => set("role", r)}
                      style={{
                        padding: "10px 8px",
                        borderRadius: "var(--radius-md)",
                        border: `1px solid ${form.role === r ? "var(--accent)" : "var(--border-default)"}`,
                        background: form.role === r ? "var(--accent-muted)" : "var(--surface-2)",
                        color: form.role === r ? "var(--accent-light)" : "var(--text-muted)",
                        cursor: "pointer",
                        fontSize: 12, fontWeight: 600, fontFamily: "var(--font-sans)",
                        display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
                        transition: "all 150ms",
                      }}
                    >
                      <i className={`bi ${roleIcon[r]}`} style={{ fontSize: 18 }} />
                      {r === "pharmacist" ? "Pharmacist" : r === "doctor" ? "Doctor" : "Admin"}
                    </button>
                  ))}
                </div>
              </div>

              {form.role === "pharmacist" && (
                <div className="pa-field">
                  <label className="pa-label">Assigned Pharmacy Branch *</label>
                  <select className="pa-select" required value={form.pharmacy_id}
                    onChange={e => set("pharmacy_id", e.target.value)}>
                    <option value="">— Select Branch —</option>
                    {meta.pharmacies.map(ph => (
                      <option key={ph.pharmacy_id} value={ph.pharmacy_id}>{ph.pharmacy_name}</option>
                    ))}
                  </select>
                </div>
              )}

              {form.role === "doctor" && (
                <div className="pa-row pa-row-2 pa-field">
                  <div>
                    <label className="pa-label">Registration No. *</label>
                    <input className="pa-input" placeholder="e.g. KMC-88412" required
                      value={form.registration_number} onChange={e => set("registration_number", e.target.value)} />
                  </div>
                  <div>
                    <label className="pa-label">Specialization *</label>
                    <input className="pa-input" placeholder="e.g. General Medicine" required
                      value={form.specialization} onChange={e => set("specialization", e.target.value)} />
                  </div>
                </div>
              )}

              <div className="pa-field">
                <label className="pa-label">Full Name *</label>
                <input className="pa-input" required minLength={2} maxLength={100}
                  placeholder={form.role === "doctor" ? "Dr. ..." : "Full name"}
                  value={form.full_name} onChange={e => set("full_name", e.target.value)} />
              </div>
            </>
          )}

          <div className="pa-field">
            <label className="pa-label">Email *</label>
            <input className="pa-input" type="email" required
              placeholder={mode === "register" && form.role === "admin" ? meta.admin_email : "you@example.com"}
              value={form.email} onChange={e => set("email", e.target.value)} />
          </div>

          <div className="pa-field">
            <label className="pa-label">Password {mode === "register" && <span style={{color:"var(--text-disabled)"}}>(min 8 chars)</span>} *</label>
            <input className="pa-input" type="password" required minLength={8}
              placeholder="••••••••"
              value={form.password} onChange={e => set("password", e.target.value)} />
          </div>

          {mode === "register" && (
            <div className="pa-field">
              <label className="pa-label">Phone</label>
              <input className="pa-input" type="tel" pattern="^\+?[0-9\-]{10,15}$"
                placeholder="+91-9845011111"
                value={form.phone} onChange={e => set("phone", e.target.value)} />
            </div>
          )}

          <button
            type="submit"
            className="pa-btn pa-btn-primary pa-btn-full"
            style={{ marginTop: 8 }}
            disabled={loading}
          >
            {loading
              ? <><div className="pa-spinner" /> Processing…</>
              : mode === "login"
                ? <><i className="bi bi-box-arrow-in-right" /> Sign In</>
                : <><i className="bi bi-person-check" /> Create Account</>
            }
          </button>
        </form>

        {mode === "login" && (
          <p style={{ marginTop: 20, fontSize: 12, color: "var(--text-muted)", textAlign: "center" }}>
            Patients track order history via the separate Patient Companion App.
          </p>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   PORTAL SHELL
   ═══════════════════════════════════════════════════════════════ */
function PortalShell({ user, onLogout, children, activeSection, setActiveSection, pendingCount }) {
  const roleMeta = {
    admin:            { badge: "role-badge-admin",   icon: "bi-shield-lock",   label: "System Admin" },
    pharmacy_manager: { badge: "role-badge-manager", icon: "bi-building",      label: "Branch Manager" },
    pharmacist:       { badge: "role-badge-pharma",  icon: "bi-capsule",       label: "Pharmacist" },
    doctor:           { badge: "role-badge-doctor",  icon: "bi-heart-pulse",   label: "Doctor" },
  };
  const rm = roleMeta[user.role] || roleMeta.pharmacist;

  const navItems = [
    ...(user.role === "admin" ? [
      { id: "approvals", icon: "bi-person-check", label: "Doctor Approvals", badge: pendingCount.doctors },
      { id: "prescriptions", icon: "bi-file-medical", label: "All Prescriptions" },
      { id: "inventory", icon: "bi-box-seam", label: "Inventory" },
    ] : []),
    ...(user.role === "pharmacy_manager" ? [
      { id: "approvals", icon: "bi-person-check", label: "Pharmacist Approvals", badge: pendingCount.pharmacists },
      { id: "extract", icon: "bi-stars", label: "AI Extractor" },
      { id: "prescriptions", icon: "bi-file-medical", label: "Dispensing Log" },
      { id: "inventory", icon: "bi-box-seam", label: "Branch Stock" },
    ] : []),
    ...(user.role === "pharmacist" ? [
      { id: "extract", icon: "bi-stars", label: "AI Extractor" },
      { id: "prescriptions", icon: "bi-file-medical", label: "Dispensing Log" },
      { id: "inventory", icon: "bi-box-seam", label: "Branch Stock" },
    ] : []),
    ...(user.role === "doctor" ? [
      { id: "extract", icon: "bi-stars", label: "AI Extractor" },
      { id: "prescriptions", icon: "bi-file-medical", label: "My Prescriptions" },
      { id: "inventory", icon: "bi-box-seam", label: "Inventory" },
    ] : []),
  ];

  const sectionTitles = {
    approvals:     user.role === "admin" ? "Doctor Approvals" : "Pharmacist Approvals",
    extract:       "AI Prescription Extractor",
    prescriptions: user.role === "pharmacist" || user.role === "pharmacy_manager"
                     ? "Dispensing Log"
                     : user.role === "doctor" ? "My Prescriptions" : "All Prescriptions",
    inventory:     user.role === "pharmacist" || user.role === "pharmacy_manager"
                     ? "Branch Stock" : "Network Inventory",
  };

  return (
    <div className="portal-layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">💊</div>
          <div className="sidebar-logo-text">
            <div className="sidebar-app-name">PharmAssist</div>
            <div className="sidebar-app-ver">AI Portal</div>
          </div>
        </div>

        <div className="sidebar-user">
          <div className="sidebar-user-name">{user.full_name}</div>
          <div className="sidebar-user-branch">
            {user.pharmacy_name || user.doctor_name || user.email}
          </div>
          <div className={`role-badge ${rm.badge}`}>
            <i className={`bi ${rm.icon}`} style={{ fontSize: 9 }} /> {rm.label}
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-section-label">Navigation</div>
          {navItems.map(item => (
            <button
              key={item.id}
              className={`sidebar-nav-item ${activeSection === item.id ? "active" : ""}`}
              onClick={() => setActiveSection(item.id)}
            >
              <i className={`bi ${item.icon} sidebar-nav-icon`} />
              {item.label}
              {item.badge > 0 && (
                <span className="sidebar-nav-badge">{item.badge}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button
            className="pa-btn pa-btn-ghost pa-btn-full"
            style={{ fontSize: 13 }}
            onClick={onLogout}
          >
            <i className="bi bi-box-arrow-left" /> Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="main-content">
        <header className="topbar">
          <div>
            <div className="topbar-title">{sectionTitles[activeSection]}</div>
            <div className="topbar-sub">
              {user.pharmacy_name ? `${user.pharmacy_name} · ` : ""}
              {new Date().toLocaleDateString("en-IN", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div className={`role-badge ${rm.badge}`}>
              <i className={`bi ${rm.icon}`} style={{ fontSize: 10 }} /> {rm.label}
            </div>
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{user.full_name}</span>
          </div>
        </header>

        <div className="page-body">
          {children}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   MAIN APP
   ═══════════════════════════════════════════════════════════════ */
export default function App() {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem("pharmassist_user") || "null"));
  const [alert, setAlert] = useState(null);
  const [activeSection, setActiveSection] = useState(null);

  const [data, setData] = useState({
    doctors: [], pharmacies: [], medicines: [], patients: [], prescriptions: [], inventory: [],
  });
  const [pendingDoctors, setPendingDoctors]           = useState([]);
  const [pendingPharmacists, setPendingPharmacists]   = useState([]);

  // Walk-in
  const [showWalkIn, setShowWalkIn]   = useState(false);
  const [walkInForm, setWalkInForm]   = useState({ full_name: "", email: "", phone: "", date_of_birth: "" });

  // NLP
  const [rawText, setRawText]         = useState("");
  const [rxImage, setRxImage]         = useState(null);
  const [extracting, setExtracting]   = useState(false);

  // Rx form
  const [rxForm, setRxForm] = useState({
    patient_id: "", doctor_id: "", pharmacy_id: "", diagnosis: "",
    medicines: [{ medicine_id: "", prescribed_dose: "1 tablet", frequency: "Twice daily", duration_days: 5, instructions: "After food" }],
  });

  // Inventory form
  const [invForm, setInvForm] = useState({ medicine_id: "", quantity_available: "", unit_price: "" });

  /* ── default section based on role ── */
  useEffect(() => {
    if (!user) return;
    const defaultSection = {
      admin: "approvals",
      pharmacy_manager: "approvals",
      pharmacist: "extract",
      doctor: "extract",
    }[user.role] || "extract";
    setActiveSection(prev => prev ?? defaultSection);
  }, [user]);

  /* ── load dashboard ── */
  const loadDashboard = useCallback(async (currentUser) => {
    try {
      const params = new URLSearchParams({
        role: currentUser.role,
        ...(currentUser.pharmacy_id ? { pharmacy_id: currentUser.pharmacy_id } : {}),
        ...(currentUser.doctor_id   ? { doctor_id:   currentUser.doctor_id }   : {}),
      });
      const res  = await fetch(`${API_BASE}/api/dashboard?${params}`);
      const json = await res.json();
      setData(json);

      if (currentUser.role === "pharmacist" || currentUser.role === "pharmacy_manager") {
        setRxForm(f => ({
          ...f,
          pharmacy_id: currentUser.pharmacy_id,
          patient_id:  f.patient_id || json.patients?.[0]?.user_id || "",
        }));
        setInvForm(f => ({
          ...f,
          medicine_id: f.medicine_id || json.medicines?.[0]?.medicine_id || "",
        }));
      }
      if (currentUser.role === "doctor") {
        setRxForm(f => ({
          ...f,
          doctor_id:  currentUser.doctor_id,
          patient_id: f.patient_id || json.patients?.[0]?.user_id || "",
        }));
      }
      if (currentUser.role === "admin") {
        const r = await fetch(`${API_BASE}/api/admin/pending-doctors?requester_role=admin`);
        const j = await r.json();
        setPendingDoctors(j.pending_doctors || []);
      }
      if (currentUser.role === "pharmacy_manager") {
        const r = await fetch(
          `${API_BASE}/api/branch/pending-pharmacists?requester_role=pharmacy_manager&requester_pharmacy_id=${currentUser.pharmacy_id}`
        );
        const j = await r.json();
        setPendingPharmacists(j.pending_pharmacists || []);
      }
    } catch {
      setAlert({ type: "danger", text: "Cannot reach the FastAPI backend on port 8000." });
    }
  }, []);

  useEffect(() => { if (user) loadDashboard(user); }, [user, loadDashboard]);

  /* ── handlers ── */
  const handleLogin  = (u) => {
    localStorage.setItem("pharmassist_user", JSON.stringify(u));
    setUser(u);
    setAlert({ type: "success", text: `Signed in as ${u.full_name}` });
  };
  const handleLogout = () => {
    localStorage.removeItem("pharmassist_user");
    setUser(null); setAlert(null); setActiveSection(null);
  };

  const handleCreateWalkIn = async (e) => {
    e.preventDefault();
    setAlert(null);
    const res  = await fetch(`${API_BASE}/api/patients`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...walkInForm, phone: walkInForm.phone || null, date_of_birth: walkInForm.date_of_birth || null }),
    });
    const json = await res.json();
    if (!res.ok) { setAlert({ type: "danger", text: Array.isArray(json.detail) ? json.detail[0].msg : json.detail }); return; }
    setWalkInForm({ full_name: "", email: "", phone: "", date_of_birth: "" });
    setShowWalkIn(false);
    await loadDashboard(user);
    setRxForm(f => ({ ...f, patient_id: json.patient.user_id }));
    setAlert({ type: "success", text: `Walk-in patient registered: ${json.patient.full_name}` });
  };

  const handleExtract = async (e) => {
    e.preventDefault();
    setExtracting(true); setAlert(null);
    const fd = new FormData();
    fd.append("raw_text", rawText);
    if (rxImage) fd.append("rx_image", rxImage);
    const res    = await fetch(`${API_BASE}/api/extract`, { method: "POST", body: fd });
    const parsed = await res.json();
    setExtracting(false);
    setRxForm(prev => ({
      ...prev,
      doctor_id: user.role === "doctor" ? user.doctor_id : parsed.resolved_doctor_id || prev.doctor_id,
      diagnosis: parsed.diagnosis || prev.diagnosis,
      medicines: parsed.medicines?.length
        ? parsed.medicines.map(m => ({
            medicine_id:    m.resolved_medicine_id || "",
            prescribed_dose: m.prescribed_dose || "1 tablet",
            frequency:       m.frequency || "Twice daily",
            duration_days:   m.duration_days || 5,
            instructions:    m.instructions || "",
          }))
        : prev.medicines,
    }));
    setAlert({ type: "info", text: "Fields extracted — review and confirm below." });
    setActiveSection("prescriptions");
  };

  const handleRxSubmit = async (e) => {
    e.preventDefault(); setAlert(null);
    const payload = {
      user_id:    Number(rxForm.patient_id),
      doctor_id:  user.role === "doctor" ? Number(user.doctor_id) : Number(rxForm.doctor_id),
      pharmacy_id: user.role === "pharmacist" || user.role === "pharmacy_manager"
        ? Number(user.pharmacy_id)
        : rxForm.pharmacy_id ? Number(rxForm.pharmacy_id) : null,
      diagnosis: rxForm.diagnosis,
      medicines: rxForm.medicines.map(m => ({
        ...m, medicine_id: Number(m.medicine_id), duration_days: Number(m.duration_days),
      })),
    };
    const res  = await fetch(`${API_BASE}/api/prescriptions`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    const json = await res.json();
    if (!res.ok) { setAlert({ type: "danger", text: Array.isArray(json.detail) ? json.detail[0].msg : json.detail }); return; }
    setAlert({ type: "success", text: json.message });
    loadDashboard(user);
  };

  const handleDispense = async (rxId) => {
    const res  = await fetch(`${API_BASE}/api/prescriptions/${rxId}/dispense?pharmacy_id=${user.pharmacy_id}`, { method: "PATCH" });
    const json = await res.json();
    if (!res.ok) { setAlert({ type: "danger", text: json.detail }); return; }
    setAlert({ type: "success", text: json.message });
    loadDashboard(user);
  };

  const handleInvSubmit = async (e) => {
    e.preventDefault(); setAlert(null);
    const res  = await fetch(`${API_BASE}/api/inventory`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        requester_role: user.role, requester_pharmacy_id: user.pharmacy_id,
        pharmacy_id: Number(user.pharmacy_id),
        medicine_id: Number(invForm.medicine_id),
        quantity_available: Number(invForm.quantity_available),
        unit_price: Number(invForm.unit_price),
      }),
    });
    const json = await res.json();
    if (!res.ok) { setAlert({ type: "danger", text: Array.isArray(json.detail) ? json.detail[0].msg : json.detail }); return; }
    setAlert({ type: "success", text: json.message });
    loadDashboard(user);
  };

  const handleAdminDecision = async (userId, action) => {
    setAlert(null);
    const res  = await fetch(`${API_BASE}/api/admin/doctors/${userId}/decision?action=${action}&requester_role=admin`, { method: "POST" });
    const json = await res.json();
    if (!res.ok) { setAlert({ type: "danger", text: json.detail }); return; }
    setAlert({ type: action === "approve" ? "success" : "warning", text: json.message });
    loadDashboard(user);
  };

  const handleManagerPharmacistDecision = async (userId, action) => {
    setAlert(null);
    const res  = await fetch(
      `${API_BASE}/api/branch/pharmacists/${userId}/decision?action=${action}&requester_role=pharmacy_manager&requester_pharmacy_id=${user.pharmacy_id}`,
      { method: "POST" }
    );
    const json = await res.json();
    if (!res.ok) { setAlert({ type: "danger", text: json.detail }); return; }
    setAlert({ type: action === "approve" ? "success" : "warning", text: json.message });
    loadDashboard(user);
  };

  const addMedRow    = () => setRxForm(f => ({ ...f, medicines: [...f.medicines, { medicine_id: "", prescribed_dose: "1 tablet", frequency: "Twice daily", duration_days: 5, instructions: "" }] }));
  const removeMedRow = (i) => setRxForm(f => ({ ...f, medicines: f.medicines.filter((_, idx) => idx !== i) }));
  const setMed = (i, k, v) => setRxForm(f => { const m = [...f.medicines]; m[i] = { ...m[i], [k]: v }; return { ...f, medicines: m }; });

  /* ── not logged in ── */
  if (!user) {
    return <AuthPage onLogin={handleLogin} alert={alert} setAlert={setAlert} />;
  }

  /* ── pending counts for sidebar badges ── */
  const pendingCount = { doctors: pendingDoctors.length, pharmacists: pendingPharmacists.length };

  /* ════════════════════════════════════════════════════════
     SECTION RENDERERS
     ════════════════════════════════════════════════════════ */

  /* ── Approvals ── */
  const renderApprovals = () => {
    if (user.role === "admin") {
      return (
        <div className="pa-card pa-card-accent-rose">
          <div className="pa-card-header">
            <div className="pa-card-title">
              <div className="pa-card-title-icon" style={{ background: "var(--rose-muted)", color: "var(--rose)" }}>
                <i className="bi bi-person-check" />
              </div>
              Pending Doctor Registrations
              {pendingDoctors.length > 0 && (
                <span className="pa-badge pa-badge-rose" style={{ marginLeft: 8 }}>
                  {pendingDoctors.length} pending
                </span>
              )}
            </div>
          </div>
          <div className="pa-table-wrap">
            <table className="pa-table">
              <thead>
                <tr>
                  <th>Doctor</th><th>Reg. No.</th><th>Specialization</th><th>Contact</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pendingDoctors.length === 0 ? (
                  <tr><td colSpan={5} className="pa-table-empty">
                    <i className="bi bi-inbox" style={{ fontSize: 28, display: "block", marginBottom: 8, opacity: 0.3 }} />
                    No pending doctor applications
                  </td></tr>
                ) : pendingDoctors.map(doc => (
                  <tr key={doc.user_id}>
                    <td><strong>{doc.full_name}</strong></td>
                    <td><span className="pa-mono">{doc.registration_number}</span></td>
                    <td>{doc.specialization}</td>
                    <td style={{ fontSize: 12 }}>{doc.email}<br />{doc.phone || "—"}</td>
                    <td>
                      <div style={{ display: "flex", gap: 8 }}>
                        <button className="pa-btn pa-btn-success pa-btn-sm"
                          onClick={() => handleAdminDecision(doc.user_id, "approve")}>
                          <i className="bi bi-check-lg" /> Approve & Save to DB
                        </button>
                        <button className="pa-btn pa-btn-danger pa-btn-sm"
                          onClick={() => handleAdminDecision(doc.user_id, "reject")}>
                          <i className="bi bi-x-lg" /> Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    }

    if (user.role === "pharmacy_manager") {
      return (
        <div className="pa-card pa-card-accent-green">
          <div className="pa-card-header">
            <div className="pa-card-title">
              <div className="pa-card-title-icon" style={{ background: "var(--emerald-muted)", color: "var(--emerald)" }}>
                <i className="bi bi-person-check" />
              </div>
              Pending Pharmacist Registrations — {user.pharmacy_name}
              {pendingPharmacists.length > 0 && (
                <span className="pa-badge pa-badge-amber" style={{ marginLeft: 8 }}>
                  {pendingPharmacists.length} pending
                </span>
              )}
            </div>
          </div>
          <div className="pa-table-wrap">
            <table className="pa-table">
              <thead>
                <tr><th>Name</th><th>Email</th><th>Phone</th><th>Branch</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {pendingPharmacists.length === 0 ? (
                  <tr><td colSpan={5} className="pa-table-empty">
                    <i className="bi bi-inbox" style={{ fontSize: 28, display: "block", marginBottom: 8, opacity: 0.3 }} />
                    No pending pharmacist applications for your branch
                  </td></tr>
                ) : pendingPharmacists.map(ph => (
                  <tr key={ph.user_id}>
                    <td><strong>{ph.full_name}</strong></td>
                    <td style={{ fontSize: 12 }}>{ph.email}</td>
                    <td style={{ fontSize: 12 }}>{ph.phone || "—"}</td>
                    <td><span className="pa-badge pa-badge-muted">Branch #{ph.pharmacy_id}</span></td>
                    <td>
                      <div style={{ display: "flex", gap: 8 }}>
                        <button className="pa-btn pa-btn-success pa-btn-sm"
                          onClick={() => handleManagerPharmacistDecision(ph.user_id, "approve")}>
                          <i className="bi bi-check-lg" /> Approve
                        </button>
                        <button className="pa-btn pa-btn-danger pa-btn-sm"
                          onClick={() => handleManagerPharmacistDecision(ph.user_id, "reject")}>
                          <i className="bi bi-x-lg" /> Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    }
    return null;
  };

  /* ── AI Extractor ── */
  const renderExtract = () => (
    <div className="pa-card pa-card-accent-violet">
      <div className="pa-card-header">
        <div className="pa-card-title">
          <div className="pa-card-title-icon" style={{ background: "var(--violet-muted)", color: "var(--violet)" }}>
            <i className="bi bi-stars" />
          </div>
          AI / NLP Prescription Extractor
          <span className="pa-badge pa-badge-violet" style={{ marginLeft: 8 }}>Groq LLM</span>
        </div>
      </div>
      <div className="pa-card-body">
        <form onSubmit={handleExtract}>
          <div className="pa-row pa-row-2" style={{ marginBottom: 16 }}>
            <div>
              <label className="pa-label">
                <i className="bi bi-textarea-t" style={{ marginRight: 5 }} />
                Clinical Note or Prescription Text
              </label>
              <input className="pa-input" type="text"
                placeholder="e.g. Dr. Meera Shenoy (KMC-45892) Diagnosis: Acute URI. Rx Dolo 650 twice daily 5 days"
                value={rawText} onChange={e => setRawText(e.target.value)} />
            </div>
            <div>
              <label className="pa-label">
                <i className="bi bi-image" style={{ marginRight: 5 }} />
                Or Upload Prescription Image
              </label>
              <input className="pa-input" type="file" accept="image/*"
                onChange={e => setRxImage(e.target.files[0])}
                style={{ cursor: "pointer" }} />
            </div>
          </div>
          <button type="submit" className="pa-btn pa-btn-primary" disabled={extracting}>
            {extracting
              ? <><div className="pa-spinner" /> Extracting with Groq…</>
              : <><i className="bi bi-stars" /> Extract Fields</>}
          </button>
          {!extracting && (
            <span style={{ marginLeft: 12, fontSize: 12, color: "var(--text-muted)" }}>
              Extracted fields will auto-populate the prescription form
            </span>
          )}
        </form>
      </div>
    </div>
  );

  /* ── Prescription form + table ── */
  const renderPrescriptions = () => {
    const isPharmacist = user.role === "pharmacist" || user.role === "pharmacy_manager";
    return (
      <>
        {/* New prescription form */}
        <div className="pa-card pa-card-accent-blue">
          <div className="pa-card-header">
            <div className="pa-card-title">
              <div className="pa-card-title-icon" style={{ background: "var(--accent-muted)", color: "var(--accent-light)" }}>
                <i className="bi bi-file-medical" />
              </div>
              {isPharmacist ? `Verify & Save Prescription — ${user.pharmacy_name}` : "Issue Digital Prescription"}
            </div>
            {isPharmacist && (
              <button className="pa-btn pa-btn-ghost pa-btn-sm"
                onClick={() => setShowWalkIn(s => !s)}>
                <i className={`bi bi-${showWalkIn ? "x-lg" : "person-plus"}`} />
                {showWalkIn ? "Cancel" : "Register Walk-In Patient"}
              </button>
            )}
          </div>

          <div className="pa-card-body">
            {/* Walk-in form */}
            {isPharmacist && showWalkIn && (
              <div className="walkin-panel">
                <div className="walkin-panel-title">
                  <i className="bi bi-person-plus" style={{ marginRight: 6 }} />
                  New Walk-In Patient
                </div>
                <form onSubmit={handleCreateWalkIn}>
                  <div className="pa-row" style={{ gridTemplateColumns: "2fr 2fr 1.5fr 1.5fr auto", alignItems: "end" }}>
                    <div>
                      <label className="pa-label">Full Name *</label>
                      <input className="pa-input" required placeholder="Patient name"
                        value={walkInForm.full_name} onChange={e => setWalkInForm({ ...walkInForm, full_name: e.target.value })} />
                    </div>
                    <div>
                      <label className="pa-label">Email *</label>
                      <input className="pa-input" type="email" required
                        value={walkInForm.email} onChange={e => setWalkInForm({ ...walkInForm, email: e.target.value })} />
                    </div>
                    <div>
                      <label className="pa-label">Phone</label>
                      <input className="pa-input" type="tel" pattern="^\+?[0-9\-]{10,15}$"
                        placeholder="+91-..."
                        value={walkInForm.phone} onChange={e => setWalkInForm({ ...walkInForm, phone: e.target.value })} />
                    </div>
                    <div>
                      <label className="pa-label">Date of Birth</label>
                      <input className="pa-input" type="date"
                        value={walkInForm.date_of_birth} onChange={e => setWalkInForm({ ...walkInForm, date_of_birth: e.target.value })} />
                    </div>
                    <div style={{ paddingBottom: 0 }}>
                      <button type="submit" className="pa-btn pa-btn-success" style={{ marginTop: 20 }}>
                        <i className="bi bi-check-lg" /> Save
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            )}

            {/* Rx form */}
            <form onSubmit={handleRxSubmit}>
              <div className="pa-row pa-row-3" style={{ marginBottom: 16 }}>
                <div>
                  <label className="pa-label">Patient *</label>
                  <select className="pa-select" required value={rxForm.patient_id}
                    onChange={e => setRxForm(f => ({ ...f, patient_id: e.target.value }))}>
                    <option value="">— Select Patient —</option>
                    {data.patients.map(pt => (
                      <option key={pt.user_id} value={pt.user_id}>
                        {pt.full_name} ({pt.phone || pt.email})
                      </option>
                    ))}
                  </select>
                </div>

                {isPharmacist ? (
                  <div>
                    <label className="pa-label">Prescribing Doctor *</label>
                    <select className="pa-select" required value={rxForm.doctor_id}
                      onChange={e => setRxForm(f => ({ ...f, doctor_id: e.target.value }))}>
                      <option value="">— Select Verified Doctor —</option>
                      {data.doctors.map(d => (
                        <option key={d.doctor_id} value={d.doctor_id}>
                          {d.doctor_name} ({d.registration_number})
                        </option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <div>
                    <label className="pa-label">Target Pharmacy</label>
                    <select className="pa-select" value={rxForm.pharmacy_id}
                      onChange={e => setRxForm(f => ({ ...f, pharmacy_id: e.target.value }))}>
                      <option value="">— Any Branch —</option>
                      {data.pharmacies.map(ph => (
                        <option key={ph.pharmacy_id} value={ph.pharmacy_id}>{ph.pharmacy_name}</option>
                      ))}
                    </select>
                  </div>
                )}

                <div>
                  <label className="pa-label">Diagnosis *</label>
                  <input className="pa-input" required placeholder="e.g. Acute Viral URI"
                    value={rxForm.diagnosis} onChange={e => setRxForm(f => ({ ...f, diagnosis: e.target.value }))} />
                </div>
              </div>

              {/* Medicine rows */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <label className="pa-label" style={{ margin: 0 }}>
                  <i className="bi bi-capsule" style={{ marginRight: 6 }} />
                  Prescribed Medicines
                </label>
                <button type="button" className="pa-btn pa-btn-ghost pa-btn-sm" onClick={addMedRow}>
                  <i className="bi bi-plus-lg" /> Add Medicine
                </button>
              </div>

              {rxForm.medicines.map((item, idx) => (
                <div key={idx} className="med-row" style={{ marginBottom: 8 }}>
                  <div>
                    <label className="pa-label">Medicine *</label>
                    <select className="pa-select" required value={item.medicine_id}
                      onChange={e => setMed(idx, "medicine_id", e.target.value)}>
                      <option value="">— Select —</option>
                      {data.medicines.map(m => (
                        <option key={m.medicine_id} value={m.medicine_id}>
                          {m.brand_name} ({m.strength})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="pa-label">Dose *</label>
                    <input className="pa-input" required value={item.prescribed_dose}
                      onChange={e => setMed(idx, "prescribed_dose", e.target.value)} />
                  </div>
                  <div>
                    <label className="pa-label">Frequency *</label>
                    <input className="pa-input" required value={item.frequency}
                      onChange={e => setMed(idx, "frequency", e.target.value)} />
                  </div>
                  <div>
                    <label className="pa-label">Days *</label>
                    <input className="pa-input" type="number" min={1} max={365} required value={item.duration_days}
                      onChange={e => setMed(idx, "duration_days", e.target.value)} />
                  </div>
                  <div>
                    <label className="pa-label">Instructions</label>
                    <input className="pa-input" placeholder="e.g. After food" value={item.instructions}
                      onChange={e => setMed(idx, "instructions", e.target.value)} />
                  </div>
                  <button type="button" className="med-row-remove" onClick={() => removeMedRow(idx)}
                    disabled={rxForm.medicines.length === 1}>
                    <i className="bi bi-trash" />
                  </button>
                </div>
              ))}

              <button type="submit" className="pa-btn pa-btn-primary" style={{ marginTop: 16 }}>
                <i className="bi bi-shield-check" /> Save & Verify Prescription
              </button>
            </form>
          </div>
        </div>

        {/* Prescriptions table */}
        <div className="pa-card">
          <div className="pa-card-header">
            <div className="pa-card-title">
              <div className="pa-card-title-icon" style={{ background: "var(--surface-3)", color: "var(--text-secondary)" }}>
                <i className="bi bi-list-columns" />
              </div>
              {isPharmacist ? `Dispensing Log — ${user.pharmacy_name}` : user.role === "doctor" ? `Prescriptions by ${user.doctor_name}` : "All System Prescriptions"}
            </div>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              {data.prescriptions.length} record{data.prescriptions.length !== 1 ? "s" : ""}
            </span>
          </div>
          <div className="pa-table-wrap">
            <table className="pa-table">
              <thead>
                <tr>
                  <th>Rx #</th><th>Date</th><th>Patient</th><th>Doctor</th>
                  <th>Diagnosis</th><th>Medicines</th><th>Status</th>
                  {isPharmacist && <th>Dispense</th>}
                </tr>
              </thead>
              <tbody>
                {data.prescriptions.length === 0 ? (
                  <tr><td colSpan={isPharmacist ? 8 : 7} className="pa-table-empty">
                    <i className="bi bi-file-earmark-x" style={{ fontSize: 28, display: "block", marginBottom: 8, opacity: 0.3 }} />
                    No prescriptions found
                  </td></tr>
                ) : data.prescriptions.map(rx => (
                  <tr key={rx.prescription_id}>
                    <td><span className="pa-mono">#{rx.prescription_id}</span></td>
                    <td style={{ fontSize: 12 }}>{rx.prescription_date}</td>
                    <td>
                      <strong>{rx.patient_name}</strong>
                      {rx.patient_phone && <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{rx.patient_phone}</div>}
                    </td>
                    <td>
                      {rx.doctor_name}
                      <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{rx.registration_number}</div>
                    </td>
                    <td>{rx.diagnosis}</td>
                    <td style={{ maxWidth: 260 }}>
                      {rx.items?.map((it, i) => (
                        <div key={i} style={{ marginBottom: i < rx.items.length - 1 ? 8 : 0 }}>
                          <strong style={{ fontSize: 13 }}>{it.brand_name}</strong>
                          <span style={{ color: "var(--text-muted)", fontSize: 12 }}>
                            {" "}— {it.prescribed_dose}, {it.frequency} ({it.duration_days}d)
                          </span>
                          {it.composition && (
                            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                              <i className="bi bi-eyedropper" style={{ marginRight: 4 }} />{it.composition}
                            </div>
                          )}
                        </div>
                      ))}
                      {rx.duplicate_ingredients?.length > 0 && (
                        <div style={{ marginTop: 6 }}>
                          <span className="ingredient-alert">
                            <i className="bi bi-exclamation-triangle-fill" />
                            Duplicate: {rx.duplicate_ingredients.join(", ")}
                          </span>
                        </div>
                      )}
                    </td>
                    <td><StatusBadge status={rx.status} /></td>
                    {isPharmacist && (
                      <td>
                        {rx.status !== "dispensed" ? (
                          <button className="pa-btn pa-btn-success pa-btn-sm"
                            onClick={() => handleDispense(rx.prescription_id)}>
                            <i className="bi bi-bag-check" /> Dispense
                          </button>
                        ) : (
                          <span style={{ fontSize: 12, color: "var(--emerald)", display: "flex", alignItems: "center", gap: 4 }}>
                            <i className="bi bi-check-circle-fill" /> Issued
                          </span>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </>
    );
  };

  /* ── Inventory ── */
  const renderInventory = () => {
    const isPharmacist = user.role === "pharmacist" || user.role === "pharmacy_manager";
    const filteredInv = isPharmacist
      ? data.inventory.filter(inv => inv.pharmacy_id === user.pharmacy_id)
      : data.inventory;

    return (
      <>
        {isPharmacist && (
          <div className="pa-card pa-card-accent-amber">
            <div className="pa-card-header">
              <div className="pa-card-title">
                <div className="pa-card-title-icon" style={{ background: "var(--amber-muted)", color: "var(--amber)" }}>
                  <i className="bi bi-box-seam" />
                </div>
                Update Branch Stock — {user.pharmacy_name}
              </div>
            </div>
            <div className="pa-card-body">
              <form onSubmit={handleInvSubmit}>
                <div className="pa-row" style={{ gridTemplateColumns: "2fr 1fr 1fr auto", alignItems: "end", gap: 12 }}>
                  <div>
                    <label className="pa-label">Medicine *</label>
                    <select className="pa-select" required value={invForm.medicine_id}
                      onChange={e => setInvForm(f => ({ ...f, medicine_id: e.target.value }))}>
                      {data.medicines.map(m => (
                        <option key={m.medicine_id} value={m.medicine_id}>
                          {m.brand_name} ({m.strength})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="pa-label">Stock Qty (≥ 0) *</label>
                    <input className="pa-input" type="number" min={0} required
                      value={invForm.quantity_available}
                      onChange={e => setInvForm(f => ({ ...f, quantity_available: e.target.value }))} />
                  </div>
                  <div>
                    <label className="pa-label">Unit Price ₹ (≥ 0) *</label>
                    <input className="pa-input" type="number" step="0.01" min={0} required
                      value={invForm.unit_price}
                      onChange={e => setInvForm(f => ({ ...f, unit_price: e.target.value }))} />
                  </div>
                  <div>
                    <button type="submit" className="pa-btn pa-btn-warning" style={{ marginTop: 20 }}>
                      <i className="bi bi-arrow-repeat" /> Update Stock
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Inventory table */}
        <div className="pa-card">
          <div className="pa-card-header">
            <div className="pa-card-title">
              <div className="pa-card-title-icon" style={{ background: "var(--surface-3)", color: "var(--text-secondary)" }}>
                <i className="bi bi-table" />
              </div>
              {isPharmacist ? `${user.pharmacy_name} — Live Stock` : "Network-Wide Inventory"}
            </div>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              {filteredInv.length} items
            </span>
          </div>
          <div className="pa-table-wrap">
            <table className="pa-table">
              <thead>
                <tr>
                  {!isPharmacist && <th>Pharmacy</th>}
                  <th>Medicine</th><th>Generic</th><th>Stock</th>
                  <th>Unit Price</th><th>Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {filteredInv.length === 0 ? (
                  <tr><td colSpan={isPharmacist ? 5 : 6} className="pa-table-empty">
                    <i className="bi bi-box" style={{ fontSize: 28, display: "block", marginBottom: 8, opacity: 0.3 }} />
                    No inventory records
                  </td></tr>
                ) : filteredInv.map((inv, idx) => (
                  <tr key={idx}>
                    {!isPharmacist && <td><strong>{inv.pharmacy_name}</strong></td>}
                    <td><strong>{inv.brand_name}</strong></td>
                    <td style={{ fontSize: 12, color: "var(--text-muted)" }}>{inv.generic_name}</td>
                    <td>
                      <span className={`pa-badge ${inv.quantity_available > 0 ? "pa-badge-green" : "pa-badge-rose"}`}>
                        {inv.quantity_available > 0 ? inv.quantity_available : "Out of stock"}
                      </span>
                    </td>
                    <td style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}>
                      ₹{Number(inv.unit_price).toFixed(2)}
                    </td>
                    <td style={{ fontSize: 12, color: "var(--text-muted)" }}>{inv.last_updated}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </>
    );
  };

  /* ── section map ── */
  const sections = {
    approvals:     renderApprovals(),
    extract:       renderExtract(),
    prescriptions: renderPrescriptions(),
    inventory:     renderInventory(),
  };

  return (
    <PortalShell
      user={user}
      onLogout={handleLogout}
      activeSection={activeSection}
      setActiveSection={(s) => { setActiveSection(s); setAlert(null); }}
      pendingCount={pendingCount}
    >
      <Alert alert={alert} onDismiss={() => setAlert(null)} />
      {sections[activeSection] ?? null}
    </PortalShell>
  );
}