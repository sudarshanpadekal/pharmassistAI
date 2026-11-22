import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function App() {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem("pharmassist_user") || "null"));
  const [authMode, setAuthMode] = useState("login");
  const [alert, setAlert] = useState(null);

  const [authForm, setAuthForm] = useState({
    full_name: "",
    email: "",
    password: "",
    phone: "",
    date_of_birth: "",
  });

  const [data, setData] = useState({
    doctors: [],
    pharmacies: [],
    medicines: [],
    prescriptions: [],
    inventory: [],
  });

  const [comparison, setComparison] = useState({ rxId: null, rows: [] });

  const [rawText, setRawText] = useState("");
  const [rxImage, setRxImage] = useState(null);
  const [extracting, setExtracting] = useState(false);

  const [rxForm, setRxForm] = useState({
    doctor_id: "",
    pharmacy_id: "",
    diagnosis: "",
    medicines: [{ medicine_id: "", prescribed_dose: "1 tablet", frequency: "Twice daily", duration_days: 5, instructions: "After food" }],
  });

  const [invForm, setInvForm] = useState({
    pharmacy_id: "",
    medicine_id: "",
    quantity_available: "",
    unit_price: "",
  });

  const loadDashboard = async (uid) => {
    try {
      const res = await fetch(`${API_BASE}/api/dashboard?user_id=${uid || ""}`);
      const json = await res.json();
      setData(json);
      if (json.pharmacies?.length && !invForm.pharmacy_id) {
        setInvForm((f) => ({ ...f, pharmacy_id: json.pharmacies[0].pharmacy_id }));
      }
      if (json.medicines?.length && !invForm.medicine_id) {
        setInvForm((f) => ({ ...f, medicine_id: json.medicines[0].medicine_id }));
      }
    } catch {
      setAlert({ type: "danger", text: "Unable to connect to FastAPI backend on port 8000." });
    }
  };

  useEffect(() => {
    if (user) loadDashboard(user.user_id);
  }, [user]);

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAlert(null);
    const endpoint = authMode === "login" ? "/api/login" : "/api/register";
    const payload =
      authMode === "login"
        ? { email: authForm.email, password: authForm.password }
        : { ...authForm, phone: authForm.phone || null, date_of_birth: authForm.date_of_birth || null };

    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const json = await res.json();
    if (!res.ok) {
      setAlert({ type: "danger", text: Array.isArray(json.detail) ? json.detail[0].msg : json.detail });
      return;
    }
    localStorage.setItem("pharmassist_user", JSON.stringify(json.user));
    setUser(json.user);
    setAlert({ type: "success", text: `Welcome, ${json.user.full_name}!` });
  };

  const handleLogout = () => {
    localStorage.removeItem("pharmassist_user");
    setUser(null);
    setAlert(null);
    setComparison({ rxId: null, rows: [] });
  };

  const handleExtract = async (e) => {
    e.preventDefault();
    setExtracting(true);
    setAlert(null);
    const formData = new FormData();
    formData.append("raw_text", rawText);
    if (rxImage) formData.append("rx_image", rxImage);

    const res = await fetch(`${API_BASE}/api/extract`, { method: "POST", body: formData });
    const parsed = await res.json();
    setExtracting(false);

    setRxForm((prev) => ({
      ...prev,
      doctor_id: parsed.resolved_doctor_id || prev.doctor_id,
      diagnosis: parsed.diagnosis || prev.diagnosis,
      medicines: parsed.medicines?.length
        ? parsed.medicines.map((m) => ({
            medicine_id: m.resolved_medicine_id || "",
            prescribed_dose: m.prescribed_dose || "1 tablet",
            frequency: m.frequency || "Twice daily",
            duration_days: m.duration_days || 5,
            instructions: m.instructions || "",
          }))
        : prev.medicines,
    }));
    setAlert({ type: "info", text: "Prescription fields extracted! Review and confirm below." });
  };

  const handleRxSubmit = async (e) => {
    e.preventDefault();
    setAlert(null);
    const payload = {
      user_id: user.user_id,
      doctor_id: Number(rxForm.doctor_id),
      pharmacy_id: rxForm.pharmacy_id ? Number(rxForm.pharmacy_id) : null,
      diagnosis: rxForm.diagnosis,
      medicines: rxForm.medicines.map((m) => ({
        ...m,
        medicine_id: Number(m.medicine_id),
        duration_days: Number(m.duration_days),
      })),
    };

    const res = await fetch(`${API_BASE}/api/prescriptions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const json = await res.json();
    if (!res.ok) {
      setAlert({ type: "danger", text: Array.isArray(json.detail) ? json.detail[0].msg : json.detail });
      return;
    }
    setAlert({ type: "success", text: json.message });
    loadDashboard(user.user_id);
  };

  const handleCompare = async (rxId) => {
    const res = await fetch(`${API_BASE}/api/compare/${rxId}`);
    const json = await res.json();
    setComparison({ rxId, rows: json.comparison || [] });
  };

  const handleInvSubmit = async (e) => {
    e.preventDefault();
    setAlert(null);
    const res = await fetch(`${API_BASE}/api/inventory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pharmacy_id: Number(invForm.pharmacy_id),
        medicine_id: Number(invForm.medicine_id),
        quantity_available: Number(invForm.quantity_available),
        unit_price: Number(invForm.unit_price),
      }),
    });
    const json = await res.json();
    if (!res.ok) {
      setAlert({ type: "danger", text: Array.isArray(json.detail) ? json.detail[0].msg : json.detail });
      return;
    }
    setAlert({ type: "success", text: json.message });
    loadDashboard(user.user_id);
  };

  if (!user) {
    return (
      <div className="container py-5">
        <div className="row justify-content-center">
          <div className="col-md-5">
            <div className="text-center mb-3">
              <h3 className="fw-bold text-primary">PharmAssist-AI</h3>
              <p className="text-muted small">React (Vite) + FastAPI + PostgreSQL (3NF)</p>
            </div>

            {alert && <div className={`alert alert-${alert.type}`}>{alert.text}</div>}

            <div className="card shadow-sm">
              <div className="card-header bg-white">
                <ul className="nav nav-pills nav-fill">
                  <li className="nav-item">
                    <button className={`nav-link ${authMode === "login" ? "active" : ""}`} onClick={() => setAuthMode("login")}>
                      Login
                    </button>
                  </li>
                  <li className="nav-item">
                    <button className={`nav-link ${authMode === "register" ? "active" : ""}`} onClick={() => setAuthMode("register")}>
                      Register Patient
                    </button>
                  </li>
                </ul>
              </div>

              <div className="card-body">
                <form onSubmit={handleAuthSubmit}>
                  {authMode === "register" && (
                    <div className="mb-2">
                      <label className="form-label fw-semibold">Full Name *</label>
                      <input
                        type="text"
                        className="form-control"
                        required
                        minLength={2}
                        maxLength={100}
                        value={authForm.full_name}
                        onChange={(e) => setAuthForm({ ...authForm, full_name: e.target.value })}
                      />
                    </div>
                  )}

                  <div className="mb-2">
                    <label className="form-label fw-semibold">Email (UNIQUE) *</label>
                    <input
                      type="email"
                      className="form-control"
                      required
                      value={authForm.email}
                      onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                    />
                  </div>

                  <div className="mb-2">
                    <label className="form-label fw-semibold">Password (Min 8 chars) *</label>
                    <input
                      type="password"
                      className="form-control"
                      required
                      minLength={8}
                      value={authForm.password}
                      onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                    />
                  </div>

                  {authMode === "register" && (
                    <div className="row g-2 mb-3">
                      <div className="col-6">
                        <label className="form-label fw-semibold">Phone</label>
                        <input
                          type="tel"
                          className="form-control"
                          pattern="^\+?[0-9\-]{10,15}$"
                          placeholder="+91-9845011111"
                          value={authForm.phone}
                          onChange={(e) => setAuthForm({ ...authForm, phone: e.target.value })}
                        />
                      </div>
                      <div className="col-6">
                        <label className="form-label fw-semibold">Date of Birth</label>
                        <input
                          type="date"
                          className="form-control"
                          max={new Date().toISOString().split("T")[0]}
                          value={authForm.date_of_birth}
                          onChange={(e) => setAuthForm({ ...authForm, date_of_birth: e.target.value })}
                        />
                      </div>
                    </div>
                  )}

                  <button type="submit" className="btn btn-primary w-100 mt-2">
                    {authMode === "login" ? "Sign In" : "Create Account"}
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-light min-vh-100 pb-5">
      <nav className="navbar navbar-dark bg-primary mb-4 shadow-sm">
        <div className="container">
          <span className="navbar-brand fw-bold">PharmAssist-AI</span>
          <div className="d-flex align-items-center gap-3 text-white">
            <span className="small">Logged in as: <strong>{user.full_name}</strong></span>
            <button className="btn btn-sm btn-outline-light" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </nav>

      <div className="container">
        {alert && <div className={`alert alert-${alert.type}`}>{alert.text}</div>}

        <div className="card mb-4 shadow-sm">
          <div className="card-header bg-dark text-white fw-semibold">
            Form 2: AI / NLP Prescription Extractor
          </div>
          <div className="card-body">
            <form onSubmit={handleExtract} className="row g-3 align-items-end">
              <div className="col-md-7">
                <label className="form-label fw-semibold">Prescription Clinical Note</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g., Dr. Meera Shenoy (KMC-45892) Diagnosis: Acute Viral URI. Rx Dolo 650 twice daily for 5 days"
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                />
              </div>
              <div className="col-md-3">
                <label className="form-label fw-semibold">Or Upload Image</label>
                <input
                  type="file"
                  accept="image/*"
                  className="form-control"
                  onChange={(e) => setRxImage(e.target.files[0])}
                />
              </div>
              <div className="col-md-2">
                <button type="submit" className="btn btn-dark w-100" disabled={extracting}>
                  {extracting ? "Extracting..." : "Extract Fields"}
                </button>
              </div>
            </form>
          </div>
        </div>

        <div className="row g-4 mb-4">
          <div className="col-lg-8">
            <div className="card h-100 shadow-sm">
              <div className="card-header bg-primary text-white fw-semibold">
                Form 3: Verified Prescription Entry (Atomic Transaction)
              </div>
              <div className="card-body">
                <form onSubmit={handleRxSubmit}>
                  <div className="row g-3 mb-3">
                    <div className="col-md-4">
                      <label className="form-label fw-semibold">Doctor *</label>
                      <select
                        className="form-select"
                        required
                        value={rxForm.doctor_id}
                        onChange={(e) => setRxForm({ ...rxForm, doctor_id: e.target.value })}
                      >
                        <option value="">-- Select Doctor --</option>
                        {data.doctors.map((d) => (
                          <option key={d.doctor_id} value={d.doctor_id}>
                            {d.doctor_name} ({d.registration_number})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="col-md-4">
                      <label className="form-label fw-semibold">Pharmacy (Optional)</label>
                      <select
                        className="form-select"
                        value={rxForm.pharmacy_id}
                        onChange={(e) => setRxForm({ ...rxForm, pharmacy_id: e.target.value })}
                      >
                        <option value="">-- Assign Later --</option>
                        {data.pharmacies.map((ph) => (
                          <option key={ph.pharmacy_id} value={ph.pharmacy_id}>
                            {ph.pharmacy_name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="col-md-4">
                      <label className="form-label fw-semibold">Diagnosis *</label>
                      <input
                        type="text"
                        className="form-control"
                        required
                        value={rxForm.diagnosis}
                        onChange={(e) => setRxForm({ ...rxForm, diagnosis: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="d-flex justify-content-between align-items-center mb-2">
                    <span className="fw-semibold small text-uppercase text-secondary">Prescribed Medicines</span>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-primary"
                      onClick={() =>
                        setRxForm({
                          ...rxForm,
                          medicines: [
                            ...rxForm.medicines,
                            { medicine_id: "", prescribed_dose: "1 tablet", frequency: "Twice daily", duration_days: 5, instructions: "" },
                          ],
                        })
                      }
                    >
                      + Add Medicine
                    </button>
                  </div>

                  {rxForm.medicines.map((item, idx) => (
                    <div key={idx} className="row g-2 mb-2 p-2 bg-light border rounded">
                      <div className="col-md-4">
                        <select
                          className="form-select form-select-sm"
                          required
                          value={item.medicine_id}
                          onChange={(e) => {
                            const updated = [...rxForm.medicines];
                            updated[idx].medicine_id = e.target.value;
                            setRxForm({ ...rxForm, medicines: updated });
                          }}
                        >
                          <option value="">-- Select Medicine * --</option>
                          {data.medicines.map((m) => (
                            <option key={m.medicine_id} value={m.medicine_id}>
                              {m.brand_name} ({m.strength})
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="col-md-2">
                        <input
                          type="text"
                          className="form-control form-control-sm"
                          placeholder="Dose *"
                          required
                          value={item.prescribed_dose}
                          onChange={(e) => {
                            const updated = [...rxForm.medicines];
                            updated[idx].prescribed_dose = e.target.value;
                            setRxForm({ ...rxForm, medicines: updated });
                          }}
                        />
                      </div>
                      <div className="col-md-2">
                        <input
                          type="text"
                          className="form-control form-control-sm"
                          placeholder="Frequency *"
                          required
                          value={item.frequency}
                          onChange={(e) => {
                            const updated = [...rxForm.medicines];
                            updated[idx].frequency = e.target.value;
                            setRxForm({ ...rxForm, medicines: updated });
                          }}
                        />
                      </div>
                      <div className="col-md-2">
                        <input
                          type="number"
                          className="form-control form-control-sm"
                          min={1}
                          max={365}
                          required
                          value={item.duration_days}
                          onChange={(e) => {
                            const updated = [...rxForm.medicines];
                            updated[idx].duration_days = e.target.value;
                            setRxForm({ ...rxForm, medicines: updated });
                          }}
                        />
                      </div>
                      <div className="col-md-2">
                        <input
                          type="text"
                          className="form-control form-control-sm"
                          placeholder="Instructions"
                          value={item.instructions}
                          onChange={(e) => {
                            const updated = [...rxForm.medicines];
                            updated[idx].instructions = e.target.value;
                            setRxForm({ ...rxForm, medicines: updated });
                          }}
                        />
                      </div>
                    </div>
                  ))}

                  <button type="submit" className="btn btn-primary mt-2">
                    Save Verified Prescription
                  </button>
                </form>
              </div>
            </div>
          </div>

          <div className="col-lg-4">
            <div className="card h-100 shadow-sm">
              <div className="card-header bg-warning text-dark fw-semibold">
                Form 4: Pharmacy Inventory Update
              </div>
              <div className="card-body">
                <form onSubmit={handleInvSubmit}>
                  <div className="mb-2">
                    <label className="form-label fw-semibold">Pharmacy *</label>
                    <select
                      className="form-select"
                      required
                      value={invForm.pharmacy_id}
                      onChange={(e) => setInvForm({ ...invForm, pharmacy_id: e.target.value })}
                    >
                      {data.pharmacies.map((ph) => (
                        <option key={ph.pharmacy_id} value={ph.pharmacy_id}>
                          {ph.pharmacy_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="mb-2">
                    <label className="form-label fw-semibold">Medicine *</label>
                    <select
                      className="form-select"
                      required
                      value={invForm.medicine_id}
                      onChange={(e) => setInvForm({ ...invForm, medicine_id: e.target.value })}
                    >
                      {data.medicines.map((m) => (
                        <option key={m.medicine_id} value={m.medicine_id}>
                          {m.brand_name} ({m.strength})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="mb-2">
                    <label className="form-label fw-semibold">Available Stock (&ge; 0) *</label>
                    <input
                      type="number"
                      className="form-control"
                      min={0}
                      required
                      value={invForm.quantity_available}
                      onChange={(e) => setInvForm({ ...invForm, quantity_available: e.target.value })}
                    />
                  </div>

                  <div className="mb-3">
                    <label className="form-label fw-semibold">Unit Price in INR (&ge; 0) *</label>
                    <input
                      type="number"
                      step="0.01"
                      min={0}
                      className="form-control"
                      required
                      value={invForm.unit_price}
                      onChange={(e) => setInvForm({ ...invForm, unit_price: e.target.value })}
                    />
                  </div>

                  <button type="submit" className="btn btn-warning w-100 fw-semibold">
                    Update Stock &amp; Price
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>

        <div className="card mb-4 shadow-sm">
          <div className="card-header bg-white fw-bold">Verified Prescriptions &amp; Active Ingredients</div>
          <div className="table-responsive">
            <table className="table table-striped align-middle mb-0">
              <thead>
                <tr>
                  <th>Rx ID</th>
                  <th>Date</th>
                  <th>Doctor</th>
                  <th>Diagnosis</th>
                  <th>Medicines &amp; Active Ingredients</th>
                  <th>Pharmacy</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.prescriptions.map((rx) => (
                  <tr key={rx.prescription_id}>
                    <td>#{rx.prescription_id}</td>
                    <td>{rx.prescription_date}</td>
                    <td>{rx.doctor_name}</td>
                    <td>{rx.diagnosis}</td>
                    <td>
                      {rx.items.map((it, i) => (
                        <div key={i} className="small">
                          <strong>{it.brand_name}</strong> — {it.prescribed_dose}, {it.frequency} ({it.duration_days}d)
                          {it.composition && <div className="text-muted">Ingredients: {it.composition}</div>}
                        </div>
                      ))}
                      {rx.duplicate_ingredients?.length > 0 && (
                        <div className="badge bg-danger mt-1">
                          Alert: Duplicate ingredient ({rx.duplicate_ingredients.join(", ")})
                        </div>
                      )}
                    </td>
                    <td>{rx.pharmacy_name}</td>
                    <td>
                      <button
                        className="btn btn-sm btn-outline-primary"
                        onClick={() => handleCompare(rx.prescription_id)}
                      >
                        Compare Pharmacies
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {comparison.rxId && (
          <div className="card mb-4 border-primary shadow-sm">
            <div className="card-header bg-primary text-white d-flex justify-content-between">
              <span>Pharmacy Availability &amp; Cost Comparison for Prescription #{comparison.rxId}</span>
              <button className="btn btn-sm btn-light" onClick={() => setComparison({ rxId: null, rows: [] })}>Close</button>
            </div>
            <div className="table-responsive">
              <table className="table mb-0">
                <thead>
                  <tr>
                    <th>Pharmacy</th>
                    <th>Address</th>
                    <th>Items In Stock</th>
                    <th>Estimated Total (&#8377;)</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.rows.map((r) => (
                    <tr key={r.pharmacy_id}>
                      <td className="fw-semibold">{r.pharmacy_name}</td>
                      <td>{r.address}</td>
                      <td>{r.in_stock_items} / {r.total_rx_items}</td>
                      <td className="fw-bold">&#8377;{Number(r.estimated_total).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="card shadow-sm">
          <div className="card-header bg-white fw-bold">Live Pharmacy Inventory</div>
          <div className="table-responsive">
            <table className="table table-striped mb-0">
              <thead>
                <tr>
                  <th>Pharmacy</th>
                  <th>Medicine</th>
                  <th>Stock</th>
                  <th>Unit Price (&#8377;)</th>
                  <th>Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {data.inventory.map((inv, idx) => (
                  <tr key={idx}>
                    <td>{inv.pharmacy_name}</td>
                    <td>{inv.brand_name}</td>
                    <td>{inv.quantity_available}</td>
                    <td>&#8377;{Number(inv.unit_price).toFixed(2)}</td>
                    <td>{inv.last_updated}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}