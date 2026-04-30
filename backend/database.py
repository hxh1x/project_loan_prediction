import sqlite3
import os
import uuid
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "lendmark.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            mpin TEXT DEFAULT '1234',
            full_name TEXT,
            phone TEXT,
            dob TEXT,
            address TEXT,
            profile_photo TEXT,
            role TEXT DEFAULT 'customer',
            account_status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS profiles (
            id TEXT PRIMARY KEY,
            user_id TEXT UNIQUE NOT NULL,
            full_name TEXT,
            account_number TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS loan_applications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            applicant_name TEXT,
            no_of_dependents INTEGER,
            education TEXT,
            self_employed TEXT,
            income_annum REAL,
            loan_amount REAL,
            loan_term INTEGER,
            cibil_score INTEGER,
            emi_day INTEGER,
            monthly_emi REAL,
            interest_rate REAL DEFAULT 10.5,
            residential_assets_value REAL,
            commercial_assets_value REAL,
            luxury_assets_value REAL,
            bank_asset_value REAL,
            prediction_status TEXT,
            confidence REAL,
            probability_of_default REAL,
            risk_score REAL,
            status TEXT DEFAULT 'pending',
            reviewed_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            balance REAL NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS emi_schedules (
            id TEXT PRIMARY KEY,
            loan_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            emi_number INTEGER,
            amount REAL,
            paid_amount REAL DEFAULT 0,
            due_date TEXT,
            status TEXT DEFAULT 'upcoming',
            payment_mode TEXT,
            transaction_id TEXT,
            late_fee REAL DEFAULT 0,
            retry_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            paid_at TEXT
        );
        CREATE TABLE IF NOT EXISTS emi_settings (
            id TEXT PRIMARY KEY,
            loan_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            auto_debit_enabled INTEGER DEFAULT 1,
            reschedule_requested INTEGER DEFAULT 0,
            requested_emi_day INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT,
            title TEXT,
            message TEXT,
            is_read INTEGER DEFAULT 0,
            loan_id TEXT,
            emi_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    
    # Schema Migration for existing databases
    try:
        cur.execute("ALTER TABLE users ADD COLUMN account_status TEXT DEFAULT 'pending'")
        cur.execute("UPDATE users SET account_status = 'approved'")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN mpin TEXT DEFAULT '1234'")
    except sqlite3.OperationalError: pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        cur.execute("ALTER TABLE users ADD COLUMN dob TEXT")
        cur.execute("ALTER TABLE users ADD COLUMN address TEXT")
    except sqlite3.OperationalError: pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT")
    except sqlite3.OperationalError: pass

    # Seed manager account if not exists
    existing = cur.execute("SELECT id FROM users WHERE email='harixx@gmail.com'").fetchone()
    if not existing:
        mgr_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO users (id, email, password_hash, full_name, role, account_status, mpin) VALUES (?,?,?,?,?,?,?)",
            (mgr_id, "harixx@gmail.com", hash_password("harixx"), "Harixx Manager", "manager", "approved", "0000")
        )
        acc_num = "ACC" + mgr_id[:8].upper()
        cur.execute(
            "INSERT INTO profiles (id, user_id, full_name, account_number) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), mgr_id, "Harixx Manager", acc_num)
        )
    db.commit()
    db.close()

def row_to_dict(row):
    return dict(row) if row else None

def rows_to_list(rows):
    return [dict(r) for r in rows]
