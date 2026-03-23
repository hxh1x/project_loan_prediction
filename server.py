"""
Lendmark - Python Flask Backend (replaces Supabase)
Run with: python3 server.py
Server starts at: http://localhost:5000
"""
import sqlite3, uuid, hashlib, json, os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

DB_PATH = os.path.join(os.path.dirname(__file__), "lendmark.db")

# ─────────────────────────────────────────────
# DB SETUP
# ─────────────────────────────────────────────
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
            full_name TEXT,
            role TEXT DEFAULT 'customer',
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
    """)
    # Seed manager account if not exists
    existing = cur.execute("SELECT id FROM users WHERE email='harixx@gmail.com'").fetchone()
    if not existing:
        mgr_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?,?,?,?,?)",
            (mgr_id, "harixx@gmail.com", hash_password("harixx"), "Harixx Manager", "manager")
        )
        acc_num = "ACC" + mgr_id[:8].upper()
        cur.execute(
            "INSERT INTO profiles (id, user_id, full_name, account_number) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), mgr_id, "Harixx Manager", acc_num)
        )
    db.commit()
    db.close()

# ─────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────
def get_current_user(req):
    token = req.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token:
        return None
    db = get_db()
    row = db.execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token=?",
        (token,)
    ).fetchone()
    db.close()
    return dict(row) if row else None

def require_auth(req):
    user = get_current_user(req)
    if not user:
        return None, jsonify({"error": "Unauthorized"}), 401
    return user, None, None

def row_to_dict(row):
    if row is None:
        return None
    return dict(row)

def rows_to_list(rows):
    return [dict(r) for r in rows]

# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────
@app.route("/api/auth/signup", methods=["POST"])
def signup():
    body = request.json or {}
    email = (body.get("email") or "").lower().strip()
    password = body.get("password", "")
    full_name = body.get("full_name", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    # Manager email is reserved
    role = "manager" if email == "harixx@gmail.com" else "customer"

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        db.close()
        return jsonify({"error": "Email already registered"}), 409

    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?,?,?,?,?)",
        (user_id, email, hash_password(password), full_name, role)
    )
    acc_num = "ACC" + user_id[:8].upper()
    db.execute(
        "INSERT INTO profiles (id, user_id, full_name, account_number) VALUES (?,?,?,?)",
        (str(uuid.uuid4()), user_id, full_name, acc_num)
    )
    db.commit()
    db.close()
    return jsonify({"message": "Account created. Please sign in."}), 201

@app.route("/api/auth/login", methods=["POST"])
def login():
    body = request.json or {}
    email = (body.get("email") or "").lower().strip()
    password = body.get("password", "")

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE email=? AND password_hash=?",
        (email, hash_password(password))
    ).fetchone()

    if not user:
        db.close()
        return jsonify({"error": "Invalid email or password"}), 401

    token = str(uuid.uuid4())
    db.execute("INSERT INTO sessions (token, user_id) VALUES (?,?)", (token, user["id"]))
    db.commit()
    db.close()

    return jsonify({
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
        }
    })

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if token:
        db = get_db()
        db.execute("DELETE FROM sessions WHERE token=?", (token,))
        db.commit()
        db.close()
    return jsonify({"message": "Logged out"})

@app.route("/api/auth/me", methods=["GET"])
def me():
    user = get_current_user(request)
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
    })

# ─────────────────────────────────────────────
# PROFILES
# ─────────────────────────────────────────────
@app.route("/api/profiles", methods=["GET"])
def get_profiles():
    user, err, code = require_auth(request)
    if err: return err, code
    if user["role"] != "manager":
        return jsonify({"error": "Forbidden"}), 403
    db = get_db()
    profiles = rows_to_list(db.execute("SELECT p.*, u.email FROM profiles p JOIN users u ON u.id = p.user_id ORDER BY p.created_at DESC").fetchall())
    db.close()
    return jsonify(profiles)

@app.route("/api/profiles/me", methods=["GET"])
def get_my_profile():
    user, err, code = require_auth(request)
    if err: return err, code
    db = get_db()
    profile = row_to_dict(db.execute("SELECT * FROM profiles WHERE user_id=?", (user["id"],)).fetchone())
    db.close()
    return jsonify(profile or {})

# ─────────────────────────────────────────────
# LOAN APPLICATIONS
# ─────────────────────────────────────────────
@app.route("/api/loan-applications", methods=["GET"])
def get_applications():
    user, err, code = require_auth(request)
    if err: return err, code
    db = get_db()
    if user["role"] == "manager":
        apps = rows_to_list(db.execute("SELECT * FROM loan_applications ORDER BY created_at DESC").fetchall())
    else:
        apps = rows_to_list(db.execute("SELECT * FROM loan_applications WHERE user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall())
    db.close()
    return jsonify(apps)

@app.route("/api/loan-applications", methods=["POST"])
def create_application():
    user, err, code = require_auth(request)
    if err: return err, code
    body = request.json or {}
    app_id = str(uuid.uuid4())
    db = get_db()
    db.execute("""
        INSERT INTO loan_applications
        (id, user_id, applicant_name, no_of_dependents, education, self_employed,
         income_annum, loan_amount, loan_term, cibil_score,
         emi_day, monthly_emi,
         residential_assets_value, commercial_assets_value, luxury_assets_value, bank_asset_value,
         prediction_status, confidence, probability_of_default, risk_score, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        app_id, user["id"],
        body.get("applicant_name", user["full_name"]),
        body.get("no_of_dependents"), body.get("education"), body.get("self_employed"),
        body.get("income_annum"), body.get("loan_amount"), body.get("loan_term"), body.get("cibil_score"),
        body.get("emi_day", 5), body.get("monthly_emi", 0),
        body.get("residential_assets_value"), body.get("commercial_assets_value"),
        body.get("luxury_assets_value"), body.get("bank_asset_value"),
        body.get("prediction_status"), body.get("confidence"),
        body.get("probability_of_default"), body.get("risk_score"), "pending"
    ))
    db.commit()
    db.close()
    return jsonify({"id": app_id, "message": "Application submitted"}), 201

@app.route("/api/loan-applications/<app_id>", methods=["PATCH"])
def update_application(app_id):
    user, err, code = require_auth(request)
    if err: return err, code
    if user["role"] != "manager":
        return jsonify({"error": "Forbidden"}), 403
    body = request.json or {}
    status = body.get("status")
    db = get_db()
    
    # Get current status before update
    cur_app = db.execute("SELECT * FROM loan_applications WHERE id=?", (app_id,)).fetchone()
    if not cur_app:
        db.close()
        return jsonify({"error": "Application not found"}), 404
        
    old_status = cur_app["status"]
    
    db.execute(
        "UPDATE loan_applications SET status=?, reviewed_at=? WHERE id=?",
        (status, datetime.utcnow().isoformat(), app_id)
    )
    
    # DISBURSEMENT: If switching from anything to 'approved'
    if status == "approved" and old_status != "approved":
        target_user_id = cur_app["user_id"]
        amount = float(cur_app["loan_amount"])
        
        # Get last balance
        last_txn = db.execute(
            "SELECT balance FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
            (target_user_id,)
        ).fetchone()
        current_balance = float(last_txn["balance"]) if last_txn else 0
        new_balance = current_balance + amount
        
        db.execute(
            "INSERT INTO transactions (id, user_id, type, amount, balance, description) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), target_user_id, "credit", amount, new_balance, f"Loan Disbursement: {app_id[:8].upper()}")
        )

    db.commit()
    db.close()
    return jsonify({"message": "Updated"})

# ─────────────────────────────────────────────
# TRANSACTIONS
# ─────────────────────────────────────────────
@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    user, err, code = require_auth(request)
    if err: return err, code
    db = get_db()
    if user["role"] == "manager":
        txns = rows_to_list(db.execute("SELECT * FROM transactions ORDER BY created_at DESC").fetchall())
    else:
        txns = rows_to_list(db.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall())
    db.close()
    return jsonify(txns)

@app.route("/api/transactions", methods=["POST"])
def create_transaction():
    user, err, code = require_auth(request)
    if err: return err, code
    if user["role"] != "manager":
        return jsonify({"error": "Forbidden"}), 403
    body = request.json or {}
    target_user_id = body.get("user_id")
    txn_type = body.get("type")  # 'credit' or 'debit'
    amount = float(body.get("amount", 0))
    description = body.get("description", "")

    db = get_db()
    last_txn = db.execute(
        "SELECT balance FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
        (target_user_id,)
    ).fetchone()
    current_balance = float(last_txn["balance"]) if last_txn else 0
    new_balance = current_balance + amount if txn_type == "credit" else current_balance - amount

    if txn_type == "debit" and new_balance < 0:
        db.close()
        return jsonify({"error": "Insufficient balance"}), 400

    txn_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO transactions (id, user_id, type, amount, balance, description) VALUES (?,?,?,?,?,?)",
        (txn_id, target_user_id, txn_type, amount, new_balance, description)
    )
    db.commit()
    db.close()
    return jsonify({"id": txn_id, "balance": new_balance}), 201

# ─────────────────────────────────────────────
# STATS (Dashboard)
# ─────────────────────────────────────────────
@app.route("/api/stats/manager", methods=["GET"])
def manager_stats():
    user, err, code = require_auth(request)
    if err: return err, code
    if user["role"] != "manager":
        return jsonify({"error": "Forbidden"}), 403
    db = get_db()
    total_customers = db.execute("SELECT COUNT(*) as c FROM users WHERE role='customer'").fetchone()["c"]
    pending_count = db.execute("SELECT COUNT(*) as c FROM loan_applications WHERE status='pending'").fetchone()["c"]
    approved_volume = db.execute("SELECT COALESCE(SUM(loan_amount),0) as s FROM loan_applications WHERE status='approved'").fetchone()["s"]
    db.close()
    return jsonify({"total_customers": total_customers, "pending_count": pending_count, "approved_volume": approved_volume})

@app.route("/api/stats/customer", methods=["GET"])
def customer_stats():
    user, err, code = require_auth(request)
    if err: return err, code
    db = get_db()
    last_txn = db.execute("SELECT balance FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user["id"],)).fetchone()
    balance = float(last_txn["balance"]) if last_txn else 0
    active_loans = db.execute("SELECT COUNT(*) as c FROM loan_applications WHERE user_id=? AND status='approved'", (user["id"],)).fetchone()["c"]
    total_apps = db.execute("SELECT COUNT(*) as c FROM loan_applications WHERE user_id=?", (user["id"],)).fetchone()["c"]
    db.close()
    return jsonify({"balance": balance, "active_loans": active_loans, "total_applications": total_apps})

# ─────────────────────────────────────────────
# STATIC FILES (Resolves local file CORS issues)
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "auth.html")

@app.route("/<path:path>")
def static_files(path):
    # Only allow serving specific file types for safety
    if any(path.endswith(ext) for ext in [".html", ".js", ".css", ".png", ".jpg", ".svg", ".ico"]):
        return send_from_directory(".", path)
    return jsonify({"error": "Not Found"}), 404

# ─────────────────────────────────────────────
# START
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("\n  ✅  Lendmark backend running at http://localhost:5001")
    print("  🚀  Open your browser at: http://localhost:5001")
    print("  📋  Manager login: harixx@gmail.com / harixx\n")
    app.run(debug=True, port=5001)
