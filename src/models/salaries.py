"""Salaries: employees (SEPARATE from the login users table) + monthly
salary payments. An employee with linked_username NULL can NEVER log in:
login consults ONLY the users table (src/utils/auth.py, server/auth.py)
- nothing here authenticates. Admin-only: every function takes a role
and raises PermissionError for non-admins. Salary payments count as
center expenses (see finance.per_center_totals)."""
import re
import sqlite3
from datetime import datetime
from src.models.finance_sync import queue_synced_row
from src.models.permissions import can_manage_salaries

MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _lang(lang):
    """Round 17: messages are single-language; lang=None -> app language."""
    if lang in ("en", "ar"):
        return lang
    try:
        from src.models.database import get_setting
        return "ar" if (get_setting("language", "en") or "en") == "ar" else "en"
    except Exception:
        return "en"


def _msg(en, ar, lang):
    return ar if _lang(lang) == "ar" else en


def _admin(role, lang=None):
    if not can_manage_salaries(role):
        raise PermissionError(_msg("salaries are admin-only", "الرواتب للمدير فقط", lang))


def ensure_tables(conn):
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS employees(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        job_title TEXT DEFAULT 'other', monthly_salary REAL DEFAULT 0,
        center_id TEXT DEFAULT 'main', linked_username TEXT,
        phone TEXT DEFAULT '', active INT DEFAULT 1, updated_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS salary_payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INT,
        month TEXT, amount REAL DEFAULT 0, payment_date TEXT,
        entered_by TEXT, center_id TEXT DEFAULT 'main', updated_at TEXT,
        FOREIGN KEY(employee_id) REFERENCES employees(id))""")
    conn.commit()


def add_employee(conn, role, name, job_title, monthly_salary, center_id,
                 linked_username=None, phone=None, lang=None):
    """Create an employee. linked_username NULL = no app login, ever.
    Returns the new id. Queued for admin-only sync."""
    _admin(role, lang)
    ensure_tables(conn)
    name = (name or "").strip()
    if not name:
        raise ValueError(_msg("employee name required", "اسم الموظف مطلوب", lang))
    if float(monthly_salary) < 0:
        raise ValueError(_msg("salary must be >= 0", "يجب أن يكون الراتب >= 0", lang))
    cur = conn.cursor()
    cur.execute("INSERT INTO employees(name, job_title, monthly_salary, center_id, linked_username, phone, active, updated_at) VALUES(?,?,?,?,?,?,1,?)",
                (name, (job_title or "other").strip(), float(monthly_salary),
                 (center_id or "main").strip(), linked_username or None, (phone or "").strip(), _now()))
    rid = cur.lastrowid
    queue_synced_row(conn, "employees", rid)
    conn.commit()
    return rid


def list_employees(conn, role, center_id=None, active_only=True, lang=None):
    """All employees (admin only), optionally for one center."""
    _admin(role, lang)
    ensure_tables(conn)
    sql, args = "SELECT * FROM employees WHERE 1=1", []
    if active_only:
        sql += " AND active=1"
    if center_id:
        sql += " AND center_id=?"
        args.append(center_id)
    return [dict(r) for r in conn.execute(sql + " ORDER BY name", args)]


def set_monthly_salary(conn, role, employee_id, amount, lang=None):
    """Change an employee's monthly salary (admin only). Re-queued for sync."""
    _admin(role, lang)
    ensure_tables(conn)
    if float(amount) < 0:
        raise ValueError(_msg("salary must be >= 0", "يجب أن يكون الراتب >= 0", lang))
    cur = conn.cursor()
    cur.execute("UPDATE employees SET monthly_salary=?, updated_at=? WHERE id=?",
                (float(amount), _now(), employee_id))
    if cur.rowcount == 0:
        raise ValueError(_msg("employee not found", "الموظف غير موجود", lang))
    queue_synced_row(conn, "employees", employee_id)
    conn.commit()


def set_employee_active(conn, role, employee_id, active, lang=None):
    """Activate / deactivate an employee (admin only). Re-queued for sync."""
    _admin(role, lang)
    ensure_tables(conn)
    cur = conn.cursor()
    cur.execute("UPDATE employees SET active=?, updated_at=? WHERE id=?",
                (1 if active else 0, _now(), employee_id))
    if cur.rowcount == 0:
        raise ValueError(_msg("employee not found", "الموظف غير موجود", lang))
    queue_synced_row(conn, "employees", employee_id)
    conn.commit()


def record_salary_payment(conn, role, employee_id, month, amount, payment_date, entered_by, lang=None):
    """Record a salary payment for month YYYY-MM. Counts as a center
    expense (the employee's center). Queued for sync (admin sees all)."""
    _admin(role, lang)
    ensure_tables(conn)
    if not MONTH_RE.match(month or ""):
        raise ValueError(_msg("month must be YYYY-MM", "الشهر بصيغة YYYY-MM", lang))
    if float(amount) <= 0:
        raise ValueError(_msg("amount must be > 0", "يجب أن يكون المبلغ > 0", lang))
    row = conn.execute("SELECT center_id, active FROM employees WHERE id=?", (employee_id,)).fetchone()
    if not row:
        raise ValueError(_msg("employee not found", "الموظف غير موجود", lang))
    if not row["active"]:
        raise ValueError(_msg("employee is inactive", "الموظف غير نشط", lang))
    cur = conn.cursor()
    cur.execute("INSERT INTO salary_payments(employee_id, month, amount, payment_date, entered_by, center_id, updated_at) VALUES(?,?,?,?,?,?,?)",
                (employee_id, month, float(amount), payment_date, entered_by, row["center_id"], _now()))
    rid = cur.lastrowid
    queue_synced_row(conn, "salary_payments", rid)
    conn.commit()
    return rid


def employee_month_status(conn, role, employee_id, month, lang=None):
    """{monthly_salary, paid, remaining} for one employee + month."""
    _admin(role, lang)
    ensure_tables(conn)
    row = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
    if not row:
        raise ValueError(_msg("employee not found", "الموظف غير موجود", lang))
    paid = conn.execute("SELECT COALESCE(SUM(amount),0) FROM salary_payments WHERE employee_id=? AND month=?",
                        (employee_id, month)).fetchone()[0]
    sal = float(row["monthly_salary"] or 0)
    return {"employee_id": employee_id, "name": row["name"], "job_title": row["job_title"],
            "center_id": row["center_id"], "month": month, "monthly_salary": sal,
            "paid": float(paid), "remaining": sal - float(paid)}


def month_summary(conn, role, month, center_id=None, lang=None):
    """Every active employee with paid/remaining for `month` (admin view)."""
    _admin(role, lang)
    return [employee_month_status(conn, role, e["id"], month, lang=lang)
            for e in list_employees(conn, role, center_id=center_id, lang=lang)]
