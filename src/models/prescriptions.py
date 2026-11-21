"""Prescriptions persistence: saved in the patient file ALWAYS,
whether printed or not. <80 lines."""
import json
from datetime import datetime
from src.models.database import get_connection, init_db

def save_prescription(patient_file, items, notes="", doctor="fady",
                      acknowledged=None):
    """items: [{generic, brand, dose, frequency, duration_days,
    instructions}]. Returns prescription id."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    d = datetime.now().strftime("%Y-%m-%d")
    cur.execute("""INSERT INTO prescriptions(patient_file,date,doctor,notes,
        acknowledged_warnings) VALUES(?,?,?,?,?)""",
        (patient_file, d, doctor, notes or "",
         json.dumps(acknowledged or [], ensure_ascii=False)))
    pid = cur.lastrowid
    for it in items:
        cur.execute("""INSERT INTO prescription_items(prescription_id,generic,
            brand,dose,frequency,duration_days,instructions)
            VALUES(?,?,?,?,?,?,?)""",
            (pid, it.get("generic", ""), it.get("brand", ""),
             it.get("dose", ""), it.get("frequency", ""),
             it.get("duration_days", ""), it.get("instructions", "")))
    conn.commit(); conn.close()
    return pid

def list_prescriptions(patient_file):
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM prescriptions WHERE patient_file=? ORDER BY id DESC",
                (patient_file,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_prescription_items(prescription_id):
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM prescription_items WHERE prescription_id=?",
                (prescription_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_prescription(prescription_id):
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM prescriptions WHERE id=?", (prescription_id,))
    r = cur.fetchone(); conn.close()
    return dict(r) if r else None
