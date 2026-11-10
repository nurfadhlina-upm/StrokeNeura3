"""
Seed script — adds 9 more varied stroke patients with
diagnoses, risk factors, treatment plans, and interventions.
Run once: python seed_patients.py
"""
import sqlite3, urllib.request, urllib.parse, json
from datetime import datetime, date, timedelta
import random

BASE = "http://localhost:5050"

def post(path, data):
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(BASE + path, data=encoded, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    urllib.request.urlopen(req)

patients = [
    # (name, age, gender, ic, contact, address, admission_offset_days)
    ("Siti Rahayu binti Mohd",    58, "Female", "660420-10-2341", "013-9876543", "Lot 5, Jalan Sejahtera, Petaling Jaya", -1),
    ("Rajesh a/l Krishnamurthy",  72, "Male",   "520814-07-5678", "017-2345678", "No. 88, Jalan Ipoh, Kuala Lumpur", -3),
    ("Lim Chee Wah",              45, "Male",   "790210-14-4321", "011-8765432", "21 Jalan Damai, Georgetown, Penang", -5),
    ("Faridah binti Hassan",      67, "Female", "590305-11-9876", "014-6543210", "Blok B-12, Taman Maju, Shah Alam", -7),
    ("Michael Tan Ah Kow",        53, "Male",   "710628-08-3456", "019-1234567", "No. 3, Lorong Utama, Johor Bahru", -2),
    ("Norliza binti Zainudin",    61, "Female", "630918-05-7654", "016-8901234", "Kampung Baru, Kuantan, Pahang", -10),
    ("Suresh a/l Pillai",         76, "Male",   "480325-07-2109", "012-5678901", "Jalan Raja Laut 4, Kuala Lumpur", -4),
    ("Wong Mei Lin",              49, "Female", "750912-10-6543", "015-3456789", "Apt 7-C, Sri Petaling, KL", -6),
    ("Azman bin Othman",          64, "Male",   "601115-03-8765", "018-9012345", "No. 44, Jalan Harmoni, Seremban", -8),
]

diagnoses = [
    # (stroke_type, nihss, onset, side, symptoms, imaging, notes)
    ("Ischemic",      14, "90 minutes",  "Left",     "Right hemiplegia, global aphasia, visual field defect",          "MRI: Left MCA infarct, penumbra present", "FAST positive; door-to-CT 18 min"),
    ("Haemorrhagic",  22, "2 hours",     "Right",    "Left hemiplegia, decreased consciousness, severe headache",      "CT: Right basal ganglia haemorrhage 25mL", "GCS 10 on arrival"),
    ("TIA",            2, "30 minutes",  "Right",    "Transient right arm weakness, slurred speech, resolved fully",   "MRI-DWI: No acute infarct",                "Symptoms resolved before arrival"),
    ("Ischemic",       8, "4 hours",     "Left",     "Right facial droop, arm drift, mild aphasia",                    "CT: Left lenticulostriate infarct",        "Hypertensive urgency on arrival"),
    ("Ischemic",      18, "Unknown",     "Bilateral","Quadriparesis, dysphagia, locked-in features",                   "MRI: Basilar artery occlusion",            "Wake-up stroke; last well previous night"),
    ("Haemorrhagic",  11, "3 hours",     "Left",     "Right arm weakness, headache, vomiting",                         "CT: Left putamen haemorrhage 12mL",        "On warfarin for AF; INR 4.2"),
    ("Ischemic",       5, "6 hours",     "Right",    "Left hand clumsiness, hemisensory loss",                         "MRI: Small right corona radiata lacune",   "NIHSS improving; likely lacunar"),
    ("TIA",            1, "15 minutes",  "Left",     "Sudden right visual loss (amaurosis fugax), resolved",           "CT: No infarct; Carotid Doppler pending",  "ABCD2 score 5 — high risk"),
    ("Ischemic",      16, "5 hours",     "Right",    "Left hemiplegia, hemispatial neglect, gaze deviation",           "CT Angio: Right MCA M1 occlusion",        "LVO confirmed; thrombectomy candidate"),
]

risk_data = [
    # hypertension, diabetes, atrial_fib, smoking, obesity, prev_stroke, heart_disease, hyperlipidemia, bp_sys, bp_dia, glucose, cholesterol, bmi
    (1, 1, 1, 0, 1, 0, 1, 1,  178, 102,  8.9, 6.1, 31.2),
    (1, 0, 1, 1, 0, 1, 1, 0,  195, 110, 11.2, 5.4, 24.1),
    (0, 0, 0, 1, 0, 0, 0, 1,  128,  78,  5.1, 7.2, 23.4),
    (1, 1, 0, 0, 1, 0, 0, 1,  165,  96,  9.8, 6.8, 29.7),
    (1, 1, 1, 1, 1, 1, 1, 1,  188, 112, 13.5, 7.1, 33.8),
    (1, 0, 1, 0, 0, 1, 0, 1,  158,  88,  6.2, 5.9, 25.6),
    (1, 1, 0, 0, 1, 1, 1, 1,  172, 100, 10.5, 6.5, 30.1),
    (0, 1, 0, 1, 0, 0, 0, 0,  135,  82,  8.3, 5.2, 22.8),
    (1, 0, 1, 1, 0, 0, 1, 1,  182, 108,  7.1, 6.3, 26.4),
]

treatment_data = [
    # tpa_eligible, tpa_given, anticoag, antiplatelet, statin, antihypertensive, other, surgery, rehab, diet
    (1, 1, "Apixaban 5mg BD",         "Aspirin 150mg OD",  "Atorvastatin 80mg",  "Ramipril 5mg",        "Metformin 1g BD",        "Nil",                      "Multidisciplinary",   "DASH diet"),
    (0, 0, "Nil",                      "Nil",               "Atorvastatin 40mg",  "Labetalol IV",        "Mannitol 20%",           "Neurosurgical evacuation", "Physiotherapy",       "Soft diet"),
    (0, 0, "Nil",                      "Aspirin 300mg stat","Atorvastatin 40mg",  "Amlodipine 5mg",      "Nil",                    "Nil",                      "None",                "Mediterranean diet"),
    (1, 0, "Nil",                      "Aspirin 150mg OD",  "Rosuvastatin 20mg",  "Ramipril 10mg",       "Metformin 500mg",        "Nil",                      "Occupational Therapy","Low-sodium diet"),
    (1, 1, "Nil",                      "Aspirin 150mg OD",  "Atorvastatin 80mg",  "Nicardipine infusion","Nil",                    "Mechanical thrombectomy",  "Multidisciplinary",   "Nasogastric feeding"),
    (0, 0, "Warfarin reversed with PCC","Nil",              "Atorvastatin 40mg",  "Amlodipine 10mg",     "Vitamin K 10mg IV",      "Nil",                      "Physiotherapy",       "Soft diet"),
    (0, 0, "Nil",                      "Clopidogrel 75mg",  "Simvastatin 40mg",   "Lisinopril 5mg",      "Metformin 500mg",        "Nil",                      "Occupational Therapy","DASH diet"),
    (0, 0, "Nil",                      "Aspirin 150mg OD",  "Atorvastatin 40mg",  "Nil",                 "Nil",                    "Carotid endarterectomy",   "None",                "Mediterranean diet"),
    (1, 1, "Nil",                      "Aspirin 150mg OD",  "Atorvastatin 80mg",  "Nicardipine infusion","Nil",                    "Mechanical thrombectomy",  "Multidisciplinary",   "DASH diet"),
]

intervention_data = [
    # list of (type, description, priority, status, days_offset)
    [("Physiotherapy",      "Upper limb motor recovery",         "High",   "In Progress", 0),
     ("Speech Therapy",     "Aphasia assessment and treatment",  "High",   "Pending",     1),
     ("Lab Tests",          "HbA1c, fasting glucose, lipids",   "Medium", "Completed",  -1)],

    [("Neurosurgical",      "Post-op monitoring ICU",            "URGENT", "In Progress", 0),
     ("Swallowing Assessment","Pre-oral intake screen",          "High",   "Completed",  -1),
     ("Psychological Support","Post-ICH anxiety counselling",    "Medium", "Pending",     3)],

    [("Imaging Follow-up",  "MRI brain + carotid Doppler",      "High",   "Pending",     1),
     ("Medication Review",  "Statin dose optimisation",          "Low",    "Pending",     5)],

    [("Physiotherapy",      "Gait retraining programme",         "High",   "In Progress", 0),
     ("Lab Tests",          "Renal function + HbA1c",           "Medium", "Completed",  -2),
     ("Medication Review",  "BP medication titration",           "High",   "Pending",     2)],

    [("Physiotherapy",      "Passive range of motion",           "High",   "In Progress", 0),
     ("Swallowing Assessment","Nasogastric tube assessment",     "URGENT", "Completed",  -1),
     ("Psychological Support","Family counselling — prognosis",  "Medium", "Pending",     2)],

    [("Lab Tests",          "INR check + renal function",        "High",   "Completed",  -1),
     ("Physiotherapy",      "Arm weakness rehabilitation",       "High",   "In Progress", 0),
     ("Medication Review",  "Anticoagulation review",            "High",   "Pending",     1)],

    [("Occupational Therapy","ADL assessment — grip strength",   "Medium", "In Progress", 0),
     ("Lab Tests",          "Lipid panel + renal function",     "Low",    "Completed",  -3)],

    [("Imaging Follow-up",  "Carotid endarterectomy follow-up", "High",   "Pending",     7),
     ("Medication Review",  "Statin + aspirin compliance check","Medium", "Pending",     7)],

    [("Physiotherapy",      "Left limb motor programme",         "High",   "In Progress", 0),
     ("Swallowing Assessment","Dysphagia screening pre-oral",    "URGENT", "Completed",  -1),
     ("Imaging Follow-up",  "MRI post-thrombectomy",            "High",   "Completed",  -1)],
]

today = date.today()

for i, (p, dx, rf, tx, ivs) in enumerate(zip(patients, diagnoses, risk_data, treatment_data, intervention_data)):
    name, age, gender, ic, contact, address, offset = p
    adm_date = str(today + timedelta(days=offset))

    # Register patient
    post("/patient/new", {
        "name": name, "age": age, "gender": gender,
        "ic_number": ic, "contact": contact,
        "address": address, "admission_date": adm_date
    })

    # Determine patient id (sequential)
    patient_id = i + 2   # patient 1 already exists

    # Diagnosis
    stroke_type, nihss, onset, side, symptoms, imaging, notes = dx
    post(f"/patient/{patient_id}/diagnosis/add", {
        "stroke_type": stroke_type, "nihss_score": nihss,
        "onset_time": onset, "affected_side": side,
        "symptoms": symptoms, "imaging_result": imaging, "notes": notes
    })

    # Risk factors
    ht, dm, af, sm, ob, ps, hd, hl, bps, bpd, gluc, chol, bmi = rf
    rf_payload = {
        "bp_systolic": bps, "bp_diastolic": bpd,
        "blood_glucose": gluc, "cholesterol": chol, "bmi": bmi
    }
    if ht: rf_payload["hypertension"] = "on"
    if dm: rf_payload["diabetes"] = "on"
    if af: rf_payload["atrial_fib"] = "on"
    if sm: rf_payload["smoking"] = "on"
    if ob: rf_payload["obesity"] = "on"
    if ps: rf_payload["prev_stroke"] = "on"
    if hd: rf_payload["heart_disease"] = "on"
    if hl: rf_payload["hyperlipidemia"] = "on"
    post(f"/patient/{patient_id}/risk/add", rf_payload)

    # Treatment
    te, tg, ac, ap, st, aht, om, si, rt, dp = tx
    tx_payload = {
        "anticoagulant": ac, "antiplatelet": ap, "statin": st,
        "antihypertensive": aht, "other_meds": om,
        "surgical_intervention": si, "rehab_type": rt, "diet_plan": dp
    }
    if te: tx_payload["tpa_eligible"] = "on"
    if tg: tx_payload["tpa_given"] = "on"
    post(f"/patient/{patient_id}/treatment/add", tx_payload)

    # Interventions
    for iv_type, iv_desc, iv_pri, iv_status, iv_offset in ivs:
        sched = str(today + timedelta(days=iv_offset)) if iv_offset >= 0 else ""
        post(f"/patient/{patient_id}/intervention/add", {
            "intervention_type": iv_type,
            "description": iv_desc,
            "priority": iv_pri,
            "status": iv_status,
            "scheduled_date": sched,
            "performed_by": random.choice(["Dr. Halim Saad", "Dr. Priya Nair", "Dr. Chen Wei", "Dr. Nurul Ain", "Dr. Subramaniam"])
        })

    print(f"✅ Added patient {patient_id}: {name}")

print("\n✅ All 9 patients seeded successfully.")
