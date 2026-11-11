"""
Stroke Patient Management System
Flask + SQLite web app with AI prediction and recommendation features.
"""

import os
import json
import sqlite3
import random
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "stroke_app_secret_2026"

# Database path — stored alongside this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "patient.db")

# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------

def init_db():
    """Create all tables if they do not exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    NOT NULL,
            age              INTEGER NOT NULL,
            gender           TEXT    NOT NULL,
            ic_number        TEXT,
            contact          TEXT,
            address          TEXT,
            admission_date   TEXT    NOT NULL,
            created_at       TEXT    NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS diagnoses (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id       INTEGER NOT NULL,
            stroke_type      TEXT    NOT NULL,
            nihss_score      INTEGER NOT NULL,
            onset_time       TEXT,
            affected_side    TEXT,
            symptoms         TEXT,
            imaging_result   TEXT,
            notes            TEXT,
            diagnosed_at     TEXT    NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS risk_factors (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id       INTEGER NOT NULL,
            hypertension     INTEGER DEFAULT 0,
            diabetes         INTEGER DEFAULT 0,
            atrial_fib       INTEGER DEFAULT 0,
            smoking          INTEGER DEFAULT 0,
            obesity          INTEGER DEFAULT 0,
            prev_stroke      INTEGER DEFAULT 0,
            heart_disease    INTEGER DEFAULT 0,
            hyperlipidemia   INTEGER DEFAULT 0,
            bp_systolic      INTEGER,
            bp_diastolic     INTEGER,
            blood_glucose    REAL,
            cholesterol      REAL,
            bmi              REAL,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS treatment_plans (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id       INTEGER NOT NULL,
            tpa_eligible     INTEGER DEFAULT 0,
            tpa_given        INTEGER DEFAULT 0,
            anticoagulant    TEXT,
            antiplatelet     TEXT,
            statin           TEXT,
            antihypertensive TEXT,
            other_meds       TEXT,
            surgical_intervention TEXT,
            rehab_type       TEXT,
            diet_plan        TEXT,
            notes            TEXT,
            created_at       TEXT    NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS interventions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id       INTEGER NOT NULL,
            intervention_type TEXT   NOT NULL,
            description      TEXT,
            priority         TEXT    DEFAULT 'Medium',
            status           TEXT    DEFAULT 'Pending',
            scheduled_date   TEXT,
            completed_date   TEXT,
            performed_by     TEXT,
            outcome          TEXT,
            created_at       TEXT    NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# AI / ML helpers (rule-based + lightweight scoring)
# ---------------------------------------------------------------------------

def predict_stroke_risk(risk_factors: dict) -> dict:
    """
    Compute a stroke recurrence risk score (0–100) using a weighted
    rule-based model inspired by clinical guidelines (CHADS2-VASc / Framingham).
    Returns score, category, and feature contributions.
    """
    score = 0
    contributions = {}

    weights = {
        "hypertension":   20,
        "atrial_fib":     18,
        "prev_stroke":    16,
        "diabetes":       10,
        "heart_disease":  10,
        "smoking":         8,
        "hyperlipidemia":  6,
        "obesity":         5,
        "age_factor":      7,  # computed below
    }

    # Binary flags
    for key in ["hypertension","atrial_fib","prev_stroke","diabetes",
                "heart_disease","smoking","hyperlipidemia","obesity"]:
        val = int(risk_factors.get(key, 0))
        contrib = round(val * weights[key])
        contributions[key.replace("_", " ").title()] = contrib
        score += contrib

    # Age factor (> 65 adds full weight; 50-65 half)
    age = int(risk_factors.get("age", 0))
    if age >= 65:
        age_contrib = weights["age_factor"]
    elif age >= 50:
        age_contrib = weights["age_factor"] // 2
    else:
        age_contrib = 0
    contributions["Age Factor"] = age_contrib
    score += age_contrib

    # Continuous vital adjustments
    bp_sys = risk_factors.get("bp_systolic", 120) or 120
    if int(bp_sys) >= 160:
        score += 5; contributions["Severe Hypertension (BP)"] = 5
    elif int(bp_sys) >= 140:
        score += 2; contributions["Elevated BP"] = 2

    glucose = risk_factors.get("blood_glucose", 5.0) or 5.0
    if float(glucose) >= 11.0:
        score += 4; contributions["High Blood Glucose"] = 4
    elif float(glucose) >= 7.8:
        score += 2; contributions["Borderline Glucose"] = 2

    bmi = risk_factors.get("bmi", 22.0) or 22.0
    if float(bmi) >= 30:
        score += 3; contributions["High BMI"] = 3

    # Cap at 100
    score = min(score, 100)

    if score < 20:
        category, color = "Low", "green"
    elif score < 50:
        category, color = "Moderate", "amber"
    elif score < 75:
        category, color = "High", "orange"
    else:
        category, color = "Very High", "red"

    return {
        "score": score,
        "category": category,
        "color": color,
        "contributions": contributions
    }


def recommend_treatment(patient_data: dict) -> dict:
    """
    Generate evidence-based treatment recommendations from patient data.
    Based on AHA/ASA 2023 stroke guidelines.
    """
    recs = {
        "medications": [],
        "interventions": [],
        "lifestyle": [],
        "monitoring": [],
        "rehabilitation": []
    }

    rf = patient_data.get("risk_factors", {})
    dx = patient_data.get("diagnosis", {})
    stroke_type = dx.get("stroke_type", "")
    nihss = int(dx.get("nihss_score", 0) or 0)
    onset = dx.get("onset_time", "")

    # ----- Medications -----
    if stroke_type == "Ischemic":
        # tPA eligibility window
        if onset and "hours" not in onset.lower():
            recs["medications"].append({
                "name": "IV Alteplase (tPA)",
                "reason": "Ischemic stroke — evaluate tPA eligibility within 4.5 h of onset",
                "priority": "URGENT"
            })
        recs["medications"].append({
            "name": "Aspirin 325 mg",
            "reason": "Antiplatelet therapy for ischemic stroke",
            "priority": "High"
        })
        recs["medications"].append({
            "name": "Statin (Atorvastatin 40–80 mg)",
            "reason": "LDL reduction & plaque stabilisation",
            "priority": "High"
        })
        if int(rf.get("atrial_fib", 0)):
            recs["medications"].append({
                "name": "Anticoagulant (Apixaban / Warfarin)",
                "reason": "AF-related cardioembolic stroke prevention",
                "priority": "High"
            })
    elif stroke_type in ("Haemorrhagic", "Hemorrhagic"):
        recs["medications"].append({
            "name": "Blood Pressure Control (Labetalol / Nicardipine)",
            "reason": "Aggressive BP management targets SBP < 140 mmHg",
            "priority": "URGENT"
        })
        recs["medications"].append({
            "name": "Reverse any anticoagulation (Vitamin K / PCC)",
            "reason": "Stop ongoing bleeding if patient on anticoagulants",
            "priority": "URGENT"
        })

    if int(rf.get("hypertension", 0)):
        recs["medications"].append({
            "name": "ACE Inhibitor / ARB (Ramipril / Losartan)",
            "reason": "Long-term hypertension management",
            "priority": "Medium"
        })
    if int(rf.get("diabetes", 0)):
        recs["medications"].append({
            "name": "Metformin / SGLT-2 Inhibitor",
            "reason": "Glycaemic control — target HbA1c < 7%",
            "priority": "Medium"
        })

    # ----- Interventions -----
    if stroke_type == "Ischemic" and nihss >= 6:
        recs["interventions"].append({
            "name": "Mechanical Thrombectomy",
            "reason": "Large vessel occlusion — consider up to 24 h with imaging selection",
            "priority": "URGENT"
        })
    if stroke_type in ("Haemorrhagic","Hemorrhagic") and nihss >= 15:
        recs["interventions"].append({
            "name": "Neurosurgical Consult / Craniotomy",
            "reason": "Large haematoma causing mass effect",
            "priority": "URGENT"
        })
    recs["interventions"].append({
        "name": "Dysphagia Screening",
        "reason": "Prevents aspiration pneumonia — perform before first oral intake",
        "priority": "High"
    })
    recs["interventions"].append({
        "name": "DVT Prophylaxis (compression stockings / LMWH)",
        "reason": "Reduce VTE risk in immobile patients",
        "priority": "High"
    })

    # ----- Rehabilitation -----
    if nihss <= 5:
        recs["rehabilitation"].append({"name": "Early Mobilisation", "reason": "Start within 24 h if stable", "priority": "High"})
        recs["rehabilitation"].append({"name": "Speech-Language Therapy", "reason": "Assess and treat aphasia/dysarthria", "priority": "Medium"})
    elif nihss <= 15:
        recs["rehabilitation"].append({"name": "Inpatient Stroke Unit Rehab", "reason": "Coordinated multidisciplinary team care", "priority": "High"})
        recs["rehabilitation"].append({"name": "Physiotherapy (5 days/week)", "reason": "Motor recovery programme", "priority": "High"})
        recs["rehabilitation"].append({"name": "Occupational Therapy", "reason": "ADL retraining and environmental adaptation", "priority": "Medium"})
    else:
        recs["rehabilitation"].append({"name": "Intensive Inpatient Rehabilitation", "reason": "Severe deficits — goal-directed intensive therapy", "priority": "High"})
        recs["rehabilitation"].append({"name": "Psychological Support / Counselling", "reason": "Post-stroke depression screening and management", "priority": "Medium"})

    # ----- Lifestyle -----
    if int(rf.get("smoking", 0)):
        recs["lifestyle"].append({"name": "Smoking Cessation", "reason": "Reduces stroke recurrence risk by ~50%", "priority": "High"})
    if int(rf.get("obesity", 0)):
        recs["lifestyle"].append({"name": "Weight Management Programme", "reason": "Target BMI 18.5–24.9", "priority": "Medium"})
    recs["lifestyle"].append({"name": "DASH / Mediterranean Diet", "reason": "Reduces BP and cardiovascular risk", "priority": "Medium"})
    recs["lifestyle"].append({"name": "Moderate Exercise (150 min/week)", "reason": "Improves cardiovascular fitness post-stroke", "priority": "Medium"})
    recs["lifestyle"].append({"name": "Alcohol Restriction", "reason": "Limit to < 14 units/week", "priority": "Low"})

    # ----- Monitoring -----
    recs["monitoring"].append({"name": "Continuous Cardiac Monitoring (48 h)", "reason": "Detect paroxysmal AF", "priority": "High"})
    recs["monitoring"].append({"name": "BP Monitoring (every 1 h initially)", "reason": "Target-guided haemodynamic management", "priority": "High"})
    recs["monitoring"].append({"name": "Fasting Lipid Panel", "reason": "Establish LDL baseline for statin titration", "priority": "Medium"})
    recs["monitoring"].append({"name": "HbA1c + Fasting Glucose", "reason": "Glycaemic status assessment", "priority": "Medium"})
    recs["monitoring"].append({"name": "MRI Brain / CT Angiography", "reason": "Vessel imaging if not yet performed", "priority": "High"})

    return recs


def compute_nihss_severity(score: int) -> dict:
    """Return severity label and prognosis hint for a NIHSS score."""
    if score == 0:
        return {"label": "No stroke symptoms", "prognosis": "Excellent", "color": "green"}
    elif score <= 4:
        return {"label": "Minor stroke", "prognosis": "Very good — most patients recover fully", "color": "emerald"}
    elif score <= 15:
        return {"label": "Moderate stroke", "prognosis": "Good with early intervention and rehab", "color": "amber"}
    elif score <= 20:
        return {"label": "Moderate–severe stroke", "prognosis": "Guarded — intensive rehabilitation needed", "color": "orange"}
    else:
        return {"label": "Severe stroke", "prognosis": "Poor — high dependency or mortality risk", "color": "red"}


# ---------------------------------------------------------------------------
# Routes — Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    patients = db.execute("""
        SELECT p.*, d.stroke_type, d.nihss_score
        FROM patients p
        LEFT JOIN diagnoses d ON d.patient_id = p.id
          AND d.id = (SELECT MAX(id) FROM diagnoses WHERE patient_id = p.id)
        ORDER BY p.created_at DESC
    """).fetchall()
    db.close()
    return render_template("index.html", patients=patients)


@app.route("/patient/new", methods=["GET", "POST"])
def new_patient():
    if request.method == "POST":
        data = request.form
        db = get_db()
        now = datetime.now().isoformat(timespec="seconds")
        cur = db.execute("""
            INSERT INTO patients (name, age, gender, ic_number, contact, address, admission_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["name"], data["age"], data["gender"],
            data.get("ic_number",""), data.get("contact",""),
            data.get("address",""), data.get("admission_date", str(date.today())), now
        ))
        patient_id = cur.lastrowid
        db.commit()
        db.close()
        flash(f"Patient '{data['name']}' registered successfully!", "success")
        return redirect(url_for("patient_detail", patient_id=patient_id))
    return render_template("new_patient.html")


@app.route("/patient/<int:patient_id>")
def patient_detail(patient_id):
    db = get_db()
    patient  = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient:
        flash("Patient not found.", "error")
        return redirect(url_for("index"))
    diagnoses   = db.execute("SELECT * FROM diagnoses WHERE patient_id = ? ORDER BY diagnosed_at DESC", (patient_id,)).fetchall()
    risk_factors = db.execute("SELECT * FROM risk_factors WHERE patient_id = ? ORDER BY id DESC LIMIT 1", (patient_id,)).fetchone()
    treatments  = db.execute("SELECT * FROM treatment_plans WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,)).fetchall()
    interventions = db.execute("SELECT * FROM interventions WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,)).fetchall()
    db.close()

    # Build AI insights if we have diagnosis + risk factor data
    ai_risk = None
    ai_recs = None
    nihss_info = None
    if diagnoses:
        latest_dx = dict(diagnoses[0])
        rf_dict = dict(risk_factors) if risk_factors else {}
        rf_dict["age"] = patient["age"]
        ai_risk = predict_stroke_risk(rf_dict)
        ai_recs = recommend_treatment({"diagnosis": latest_dx, "risk_factors": rf_dict})
        nihss_info = compute_nihss_severity(int(latest_dx.get("nihss_score", 0)))

    return render_template("patient_detail.html",
        patient=patient,
        diagnoses=diagnoses,
        risk_factors=risk_factors,
        treatments=treatments,
        interventions=interventions,
        ai_risk=ai_risk,
        ai_recs=ai_recs,
        nihss_info=nihss_info
    )


@app.route("/patient/<int:patient_id>/delete", methods=["POST"])
def delete_patient(patient_id):
    db = get_db()
    patient = db.execute("SELECT name FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if patient:
        db.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        db.commit()
        flash(f"Patient '{patient['name']}' deleted.", "info")
    db.close()
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Routes — Sub-forms (diagnosis, risk factors, treatment, intervention)
# ---------------------------------------------------------------------------

@app.route("/patient/<int:patient_id>/diagnosis/add", methods=["POST"])
def add_diagnosis(patient_id):
    data = request.form
    db = get_db()
    db.execute("""
        INSERT INTO diagnoses (patient_id, stroke_type, nihss_score, onset_time,
            affected_side, symptoms, imaging_result, notes, diagnosed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (patient_id, data["stroke_type"], data["nihss_score"],
          data.get("onset_time",""), data.get("affected_side",""),
          data.get("symptoms",""), data.get("imaging_result",""),
          data.get("notes",""), datetime.now().isoformat(timespec="seconds")))
    db.commit(); db.close()
    flash("Diagnosis recorded.", "success")
    return redirect(url_for("patient_detail", patient_id=patient_id))


@app.route("/patient/<int:patient_id>/risk/add", methods=["POST"])
def add_risk_factors(patient_id):
    data = request.form
    db = get_db()
    # Upsert — delete old, insert new
    db.execute("DELETE FROM risk_factors WHERE patient_id = ?", (patient_id,))
    db.execute("""
        INSERT INTO risk_factors (patient_id, hypertension, diabetes, atrial_fib,
            smoking, obesity, prev_stroke, heart_disease, hyperlipidemia,
            bp_systolic, bp_diastolic, blood_glucose, cholesterol, bmi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        patient_id,
        int("hypertension" in data), int("diabetes" in data),
        int("atrial_fib" in data), int("smoking" in data),
        int("obesity" in data), int("prev_stroke" in data),
        int("heart_disease" in data), int("hyperlipidemia" in data),
        data.get("bp_systolic") or None, data.get("bp_diastolic") or None,
        data.get("blood_glucose") or None, data.get("cholesterol") or None,
        data.get("bmi") or None
    ))
    db.commit(); db.close()
    flash("Risk factors updated.", "success")
    return redirect(url_for("patient_detail", patient_id=patient_id))


@app.route("/patient/<int:patient_id>/treatment/add", methods=["POST"])
def add_treatment(patient_id):
    data = request.form
    db = get_db()
    db.execute("""
        INSERT INTO treatment_plans (patient_id, tpa_eligible, tpa_given,
            anticoagulant, antiplatelet, statin, antihypertensive, other_meds,
            surgical_intervention, rehab_type, diet_plan, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (patient_id,
          int("tpa_eligible" in data), int("tpa_given" in data),
          data.get("anticoagulant",""), data.get("antiplatelet",""),
          data.get("statin",""), data.get("antihypertensive",""),
          data.get("other_meds",""), data.get("surgical_intervention",""),
          data.get("rehab_type",""), data.get("diet_plan",""),
          data.get("notes",""), datetime.now().isoformat(timespec="seconds")))
    db.commit(); db.close()
    flash("Treatment plan saved.", "success")
    return redirect(url_for("patient_detail", patient_id=patient_id))


@app.route("/patient/<int:patient_id>/intervention/add", methods=["POST"])
def add_intervention(patient_id):
    data = request.form
    db = get_db()
    db.execute("""
        INSERT INTO interventions (patient_id, intervention_type, description,
            priority, status, scheduled_date, performed_by, outcome, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (patient_id, data["intervention_type"], data.get("description",""),
          data.get("priority","Medium"), data.get("status","Pending"),
          data.get("scheduled_date",""), data.get("performed_by",""),
          data.get("outcome",""), datetime.now().isoformat(timespec="seconds")))
    db.commit(); db.close()
    flash("Intervention scheduled.", "success")
    return redirect(url_for("patient_detail", patient_id=patient_id))


@app.route("/patient/<int:patient_id>/intervention/<int:iid>/delete", methods=["POST"])
def delete_intervention(patient_id, iid):
    db = get_db()
    db.execute("DELETE FROM interventions WHERE id = ? AND patient_id = ?", (iid, patient_id))
    db.commit(); db.close()
    flash("Intervention removed.", "info")
    return redirect(url_for("patient_detail", patient_id=patient_id))


# ---------------------------------------------------------------------------
# API endpoints (JSON) for dashboard widgets
# ---------------------------------------------------------------------------

@app.route("/api/stats")
def api_stats():
    db = get_db()
    total     = db.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    ischemic  = db.execute("SELECT COUNT(DISTINCT patient_id) FROM diagnoses WHERE stroke_type='Ischemic'").fetchone()[0]
    haemo     = db.execute("SELECT COUNT(DISTINCT patient_id) FROM diagnoses WHERE stroke_type LIKE 'H%morrhagic'").fetchone()[0]
    tia       = db.execute("SELECT COUNT(DISTINCT patient_id) FROM diagnoses WHERE stroke_type='TIA'").fetchone()[0]
    pending_i = db.execute("SELECT COUNT(*) FROM interventions WHERE status='Pending'").fetchone()[0]
    db.close()
    return jsonify({"total": total, "ischemic": ischemic, "haemorrhagic": haemo,
                    "tia": tia, "pending_interventions": pending_i})


@app.route("/api/risk_predict", methods=["POST"])
def api_risk_predict():
    data = request.json or {}
    result = predict_stroke_risk(data)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Hospital Intelligence — population-level AI analytics
# ---------------------------------------------------------------------------

def hospital_intelligence_ai(db) -> dict:
    """
    Runs population-level AI analysis across all patients.
    Returns structured insights, risk stratification, alerts, and recommendations.
    """
    # ── Raw data collection ──────────────────────────────────────────────
    all_patients = db.execute("""
        SELECT p.id, p.name, p.age, p.gender, p.admission_date,
               d.stroke_type, d.nihss_score, d.onset_time, d.affected_side,
               r.hypertension, r.diabetes, r.atrial_fib, r.smoking, r.obesity,
               r.prev_stroke, r.heart_disease, r.hyperlipidemia,
               r.bp_systolic, r.blood_glucose, r.bmi,
               t.tpa_eligible, t.tpa_given, t.rehab_type
        FROM patients p
        LEFT JOIN diagnoses d ON d.patient_id = p.id
          AND d.id = (SELECT MAX(id) FROM diagnoses WHERE patient_id = p.id)
        LEFT JOIN risk_factors r ON r.patient_id = p.id
          AND r.id = (SELECT MAX(id) FROM risk_factors WHERE patient_id = p.id)
        LEFT JOIN treatment_plans t ON t.patient_id = p.id
          AND t.id = (SELECT MAX(id) FROM treatment_plans WHERE patient_id = p.id)
        ORDER BY p.id
    """).fetchall()

    interventions_all = db.execute("""
        SELECT patient_id, intervention_type, priority, status FROM interventions
    """).fetchall()

    # ── Basic counts ─────────────────────────────────────────────────────
    total = len(all_patients)
    if total == 0:
        return {"empty": True}

    stroke_counts = {"Ischemic": 0, "Haemorrhagic": 0, "Hemorrhagic": 0, "TIA": 0, "Unknown": 0, "None": 0}
    for p in all_patients:
        st = p["stroke_type"] or "None"
        stroke_counts[st] = stroke_counts.get(st, 0) + 1

    # Merge Haemorrhagic spellings
    haemo_total = stroke_counts.get("Haemorrhagic", 0) + stroke_counts.get("Hemorrhagic", 0)

    # ── NIHSS distribution ──────────────────────────────────────────────
    nihss_bands = {"No Symptoms (0)": 0, "Minor (1-4)": 0,
                   "Moderate (5-15)": 0, "Mod-Severe (16-20)": 0, "Severe (21+)": 0}
    nihss_values = []
    for p in all_patients:
        n = p["nihss_score"]
        if n is None:
            continue
        nihss_values.append(n)
        if n == 0: nihss_bands["No Symptoms (0)"] += 1
        elif n <= 4: nihss_bands["Minor (1-4)"] += 1
        elif n <= 15: nihss_bands["Moderate (5-15)"] += 1
        elif n <= 20: nihss_bands["Mod-Severe (16-20)"] += 1
        else: nihss_bands["Severe (21+)"] += 1

    avg_nihss = round(sum(nihss_values) / len(nihss_values), 1) if nihss_values else 0

    # ── Risk factor prevalence ───────────────────────────────────────────
    rf_fields = ["hypertension", "diabetes", "atrial_fib", "smoking",
                 "obesity", "prev_stroke", "heart_disease", "hyperlipidemia"]
    rf_labels = ["Hypertension", "Diabetes", "Atrial Fibrillation", "Smoking",
                 "Obesity", "Prev. Stroke/TIA", "Heart Disease", "Hyperlipidaemia"]
    rf_counts = {f: 0 for f in rf_fields}
    for p in all_patients:
        for f in rf_fields:
            if p[f]:
                rf_counts[f] += 1
    rf_prevalence = [
        {"label": lbl, "field": f, "count": rf_counts[f],
         "pct": round(rf_counts[f] / total * 100)}
        for f, lbl in zip(rf_fields, rf_labels)
    ]
    rf_prevalence.sort(key=lambda x: x["count"], reverse=True)

    # ── Per-patient risk scores ──────────────────────────────────────────
    patient_risks = []
    for p in all_patients:
        rf_dict = {f: (p[f] or 0) for f in rf_fields}
        rf_dict["age"] = p["age"] or 0
        rf_dict["bp_systolic"] = p["bp_systolic"] or 120
        rf_dict["blood_glucose"] = p["blood_glucose"] or 5.0
        rf_dict["bmi"] = p["bmi"] or 22.0
        risk = predict_stroke_risk(rf_dict)
        nihss_i = compute_nihss_severity(int(p["nihss_score"] or 0))
        patient_risks.append({
            "id": p["id"],
            "name": p["name"],
            "age": p["age"],
            "gender": p["gender"],
            "stroke_type": p["stroke_type"] or "—",
            "nihss_score": p["nihss_score"],
            "nihss_label": nihss_i["label"],
            "nihss_color": nihss_i["color"],
            "risk_score": risk["score"],
            "risk_category": risk["category"],
            "risk_color": risk["color"],
            "admission_date": p["admission_date"],
            "tpa_eligible": p["tpa_eligible"],
            "tpa_given": p["tpa_given"],
        })
    patient_risks.sort(key=lambda x: x["risk_score"], reverse=True)

    risk_dist = {"Very High": 0, "High": 0, "Moderate": 0, "Low": 0}
    for pr in patient_risks:
        risk_dist[pr["risk_category"]] = risk_dist.get(pr["risk_category"], 0) + 1

    # ── tPA stats ────────────────────────────────────────────────────────
    tpa_eligible = sum(1 for p in all_patients if p["tpa_eligible"])
    tpa_given    = sum(1 for p in all_patients if p["tpa_given"])

    # ── Intervention summary ─────────────────────────────────────────────
    iv_status_counts = {"Pending": 0, "In Progress": 0, "Completed": 0, "Cancelled": 0}
    iv_urgent = 0
    for iv in interventions_all:
        s = iv["status"]
        iv_status_counts[s] = iv_status_counts.get(s, 0) + 1
        if iv["priority"] == "URGENT" and iv["status"] in ("Pending", "In Progress"):
            iv_urgent += 1

    # ── Critical alerts ──────────────────────────────────────────────────
    alerts = []
    for pr in patient_risks:
        if pr["risk_category"] == "Very High":
            alerts.append({
                "level": "critical",
                "patient_id": pr["id"],
                "patient_name": pr["name"],
                "message": f"Very High recurrence risk (score {pr['risk_score']}/100) — escalate preventive management",
                "icon": "🔴"
            })
        nihss_v = pr["nihss_score"]
        if nihss_v and int(nihss_v) >= 16:
            alerts.append({
                "level": "warning",
                "patient_id": pr["id"],
                "patient_name": pr["name"],
                "message": f"Severe neurological deficit (NIHSS {nihss_v}) — intensive rehab & monitoring required",
                "icon": "🟠"
            })

    for iv in interventions_all:
        if iv["priority"] == "URGENT" and iv["status"] == "Pending":
            p_name = next((pr["name"] for pr in patient_risks if pr["id"] == iv["patient_id"]), f"Patient #{iv['patient_id']}")
            alerts.append({
                "level": "critical",
                "patient_id": iv["patient_id"],
                "patient_name": p_name,
                "message": f"URGENT intervention pending: {iv['intervention_type']}",
                "icon": "⚠️"
            })

    # ── Population-level AI recommendations ─────────────────────────────
    pop_recs = []

    # Hypertension
    ht_pct = rf_counts["hypertension"] / total * 100
    if ht_pct >= 50:
        pop_recs.append({
            "category": "Blood Pressure",
            "icon": "🫀",
            "priority": "High",
            "title": f"Hypertension highly prevalent ({ht_pct:.0f}% of patients)",
            "detail": "Implement structured BP protocol: target SBP < 130 mmHg for ischemic, < 140 mmHg post-haemorrhagic. Consider dedicated hypertension nurse-led clinic.",
            "evidence": "AHA/ASA 2023 — Class I, Level A"
        })

    # AF
    af_pct = rf_counts["atrial_fib"] / total * 100
    if af_pct >= 30:
        pop_recs.append({
            "category": "Anticoagulation",
            "icon": "💊",
            "priority": "High",
            "title": f"Atrial fibrillation in {af_pct:.0f}% of patients — anticoagulation audit needed",
            "detail": "Review all AF patients for anticoagulation status. Prioritise DOAC (Apixaban/Rivaroxaban) over warfarin unless contraindicated. CHA₂DS₂-VASc-guided therapy.",
            "evidence": "ESC 2023 AF Guidelines — Class I, Level A"
        })

    # Diabetes
    dm_pct = rf_counts["diabetes"] / total * 100
    if dm_pct >= 40:
        pop_recs.append({
            "category": "Glycaemic Control",
            "icon": "🩸",
            "priority": "Medium",
            "title": f"Diabetes prevalent in {dm_pct:.0f}% — structured glycaemic management required",
            "detail": "Ensure all diabetic patients have HbA1c target < 7%. SGLT-2 inhibitors preferred for cardioprotection. Refer to endocrinology for optimisation.",
            "evidence": "ADA Standards of Medical Care 2024"
        })

    # Smoking
    sm_pct = rf_counts["smoking"] / total * 100
    if sm_pct >= 20:
        pop_recs.append({
            "category": "Smoking Cessation",
            "icon": "🚭",
            "priority": "Medium",
            "title": f"{sm_pct:.0f}% of patients are active smokers — cessation programme indicated",
            "detail": "Implement inpatient smoking cessation counselling. Offer NRT, Varenicline or Bupropion on discharge. Follow-up at 4 weeks post-discharge.",
            "evidence": "AHA/ASA 2023 — Class I, Level B"
        })

    # tPA gap
    ischemic_count = stroke_counts.get("Ischemic", 0)
    if ischemic_count > 0 and tpa_eligible > tpa_given:
        gap = tpa_eligible - tpa_given
        pop_recs.append({
            "category": "Thrombolysis",
            "icon": "⏱️",
            "priority": "High",
            "title": f"{gap} tPA-eligible patient(s) did not receive thrombolysis",
            "detail": "Review door-to-needle times. Audit tPA contraindications documentation. Target door-to-needle time < 60 minutes. Consider stroke code activation protocol.",
            "evidence": "AHA/ASA 2023 — Class I, Level A"
        })

    # Severe NIHSS
    severe_count = nihss_bands.get("Severe (21+)", 0) + nihss_bands.get("Mod-Severe (16-20)", 0)
    if severe_count > 0:
        pop_recs.append({
            "category": "Rehabilitation",
            "icon": "🏃",
            "priority": "High",
            "title": f"{severe_count} patient(s) with moderate-severe neurological deficits",
            "detail": "Ensure early mobilisation within 24–48 h for stable patients. Dedicated physiotherapy and OT 5 days/week. Consider early transfer to specialist stroke rehab unit.",
            "evidence": "NICE Stroke Guideline NG128"
        })

    # Very high risk patients
    if risk_dist["Very High"] > 0:
        pop_recs.append({
            "category": "Secondary Prevention",
            "icon": "🛡️",
            "priority": "High",
            "title": f"{risk_dist['Very High']} patient(s) classified as Very High recurrence risk",
            "detail": "Expedite secondary prevention: dual antiplatelet therapy for 21 days (ischemic), intensive lipid lowering (LDL < 1.4 mmol/L), BP optimisation, and lifestyle intervention bundle.",
            "evidence": "POINT Trial / AHA/ASA 2023"
        })

    # Avg NIHSS context
    if avg_nihss > 10:
        pop_recs.append({
            "category": "Stroke Unit",
            "icon": "🏥",
            "priority": "Medium",
            "title": f"Average NIHSS of {avg_nihss} indicates a moderate-to-severe case mix",
            "detail": "Ensure adequate stroke unit bed capacity. Consider swallowing assessment protocol for all NIHSS > 5 patients before oral intake. Implement standardised care bundles.",
            "evidence": "RCP Sentinel Stroke National Audit Programme (SSNAP)"
        })

    # Obesity
    ob_pct = rf_counts["obesity"] / total * 100
    if ob_pct >= 30:
        pop_recs.append({
            "category": "Weight Management",
            "icon": "⚖️",
            "priority": "Low",
            "title": f"Obesity in {ob_pct:.0f}% of patients — structured weight management on discharge",
            "detail": "Refer to dietitian for DASH / Mediterranean diet counselling. Set BMI targets at follow-up. Consider bariatric referral for BMI > 35 with comorbidities.",
            "evidence": "WHO Obesity guidelines 2022"
        })

    # Sort by priority
    pri_order = {"High": 0, "Medium": 1, "Low": 2}
    pop_recs.sort(key=lambda x: pri_order.get(x["priority"], 3))

    # ── Age & gender breakdown ───────────────────────────────────────────
    ages = [p["age"] for p in all_patients if p["age"]]
    avg_age = round(sum(ages) / len(ages), 1) if ages else 0
    male_count   = sum(1 for p in all_patients if p["gender"] == "Male")
    female_count = sum(1 for p in all_patients if p["gender"] == "Female")
    age_bands = {"< 50": 0, "50–64": 0, "65–74": 0, "75+": 0}
    for a in ages:
        if a < 50: age_bands["< 50"] += 1
        elif a < 65: age_bands["50–64"] += 1
        elif a < 75: age_bands["65–74"] += 1
        else: age_bands["75+"] += 1

    return {
        "empty": False,
        "total": total,
        "avg_age": avg_age,
        "avg_nihss": avg_nihss,
        "male_count": male_count,
        "female_count": female_count,
        "stroke_counts": {
            "Ischemic": stroke_counts.get("Ischemic", 0),
            "Haemorrhagic": haemo_total,
            "TIA": stroke_counts.get("TIA", 0),
            "Unknown/None": stroke_counts.get("Unknown", 0) + stroke_counts.get("None", 0),
        },
        "nihss_bands": nihss_bands,
        "rf_prevalence": rf_prevalence,
        "risk_dist": risk_dist,
        "patient_risks": patient_risks,
        "tpa_eligible": tpa_eligible,
        "tpa_given": tpa_given,
        "iv_status_counts": iv_status_counts,
        "iv_urgent": iv_urgent,
        "alerts": alerts,
        "pop_recs": pop_recs,
        "age_bands": age_bands,
    }


@app.route("/intelligence")
def hospital_intelligence():
    db = get_db()
    data = hospital_intelligence_ai(db)
    db.close()
    return render_template("intelligence.html", d=data)


@app.route("/api/intelligence")
def api_intelligence():
    db = get_db()
    data = hospital_intelligence_ai(db)
    db.close()
    # Make JSON-serialisable
    return jsonify(data)


# Ensure tables exist on import (needed for Render/Gunicorn)
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"\n✅ Stroke Patient Management System started")
    print(f"📂 Database: {DB_PATH}")
    print(f"🌐 URL: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
