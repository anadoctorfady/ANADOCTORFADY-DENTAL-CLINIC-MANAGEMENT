"""DB: init, insert, search, finance."""
from src.models.database import init_db, get_connection
from src.models.finance import net_income
def test_init():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    names = {r[0] for r in cur.fetchall()}; conn.close()
    assert "patients" in names and "users" in names and "appointments" in names
def test_insert_search():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,father_name,grand_name,last_name,full_name,birth_date_greg,mobile1,emergency_phone,nationality) VALUES(?,?,?,?,?,?,?,?,?)",
                ("Test", "Father", "Grand", "Last", "Test Father Grand Last", "2000-01-01", "0944111222", "0999888777", "سورية"))
    fid = cur.lastrowid; conn.commit()
    cur.execute("SELECT * FROM patients WHERE mobile1=?", ("0944111222",))
    assert cur.fetchone() is not None
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,)); conn.commit(); conn.close()
def test_finance():
    init_db()
    res = net_income()
    assert set(res) >= {"total_income", "net_income", "total_debts"}
