"""
Lendmark - Python Flask Backend
Modularized Version
"""
import os, sys, uuid, socket, calendar
from datetime import datetime, date

# Ensure local modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import ml_model
from database import get_db, init_db, hash_password, row_to_dict, rows_to_list
from auth_utils import require_auth, get_current_user
from emi_engine import generate_emi_schedule, process_emi_engine, _notify

app = Flask(__name__)
CORS(app, supports_credentials=True)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
UPLOAD_FOLDER = os.path.join(ROOT_DIR, "data", "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────
@app.route("/api/auth/signup", methods=["POST"])
def signup():
    body = request.json or {}
    email = (body.get("email") or "").lower().strip()
    password = body.get("password", "")
    full_name = body.get("full_name", "")
    mpin = body.get("mpin", "1234")
    phone = body.get("phone", "")
    dob = body.get("dob", "")
    address = body.get("address", "")
    
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    role = "manager" if email == "harixx@gmail.com" else "customer"
    account_status = "approved" if role == "manager" else "pending"

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        db.close()
        return jsonify({"error": "Email already registered"}), 409

    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (id, email, password_hash, mpin, full_name, phone, dob, address, role, account_status) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (user_id, email, hash_password(password), mpin, full_name, phone, dob, address, role, account_status)
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

    user_dict = dict(user)
    if user_dict.get("account_status") == "pending":
        db.close()
        return jsonify({"error": "Account pending manager approval"}), 403
    if user_dict.get("account_status") == "rejected":
        db.close()
        return jsonify({"error": "Account rejected by manager"}), 403

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
        "mpin": user["mpin"],
        "phone": user["phone"],
        "dob": user["dob"],
        "address": user["address"],
        "profile_photo": user["profile_photo"]
    })

@app.route("/api/auth/profile-photo", methods=["POST"])
def upload_profile_photo():
    user, err, code = require_auth(request)
    if err: return err, code
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        ext = file.filename.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png', 'gif']:
            return jsonify({"error": "Invalid file type"}), 400
            
        filename = f"{user['id']}_{int(datetime.utcnow().timestamp())}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        db = get_db()
        db.execute("UPDATE users SET profile_photo=? WHERE id=?", (filename, user["id"]))
        db.commit()
        db.close()
        
        return jsonify({"message": "Photo uploaded", "filename": filename})

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/api/auth/profile", methods=["POST"])
def update_profile():
    user, err, code = require_auth(request)
    if err: return err, code
    body = request.json or {}
    full_name = body.get("full_name", user["full_name"])
    email = body.get("email", user["email"])
    mpin = body.get("mpin", user["mpin"])
    phone = body.get("phone", user["phone"])
    dob = body.get("dob", user["dob"])
    address = body.get("address", user["address"])
    password = body.get("password")

    if mpin and (not mpin.isdigit() or len(mpin) != 4):
        return jsonify({"error": "MPIN must be 4 digits"}), 400

    db = get_db()
    if password:
        db.execute("UPDATE users SET full_name=?, email=?, mpin=?, phone=?, dob=?, address=?, password_hash=? WHERE id=?",
                   (full_name, email, mpin, phone, dob, address, hash_password(password), user["id"]))
    else:
        db.execute("UPDATE users SET full_name=?, email=?, mpin=?, phone=?, dob=?, address=? WHERE id=?",
                   (full_name, email, mpin, phone, dob, address, user["id"]))
    db.commit()
    db.close()
    return jsonify({"message": "Profile updated", "user": {"full_name": full_name, "email": email, "mpin": mpin, "phone": phone, "dob": dob, "address": address}})

# ─────────────────────────────────────────────
# PROFILES & CUSTOMERS
# ─────────────────────────────────────────────
@app.route("/api/profiles", methods=["GET"])
def get_profiles():
    user, err, code = require_auth(request)
    if err: return err, code
    if user["role"] != "manager":
        return jsonify({"error": "Forbidden"}), 403
    db = get_db()
    profiles = rows_to_list(db.execute("SELECT p.account_number, u.id as user_id, u.full_name, u.email, u.account_status, u.profile_photo, u.phone, u.dob FROM profiles p JOIN users u ON u.id = p.user_id ORDER BY p.created_at DESC").fetchall())
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

@app.route("/api/users/<user_id>/status", methods=["PATCH"])
def update_user_status(user_id):
    user, err, code = require_auth(request)
    if err: return err, code
    if user["role"] != "manager":
        return jsonify({"error": "Forbidden"}), 403
    body = request.json or {}
    status = body.get("status")
    if status not in ["approved", "rejected", "pending"]:
        return jsonify({"error": "Invalid status"}), 400
    db = get_db()
    db.execute("UPDATE users SET account_status=? WHERE id=?", (status, user_id))
    db.commit()
    db.close()
    return jsonify({"message": f"User status updated to {status}"})

@app.route("/api/manager/customer/<user_id>", methods=["GET"])
def get_customer_full_details(user_id):
    user, err, code = require_auth(request)
    if err: return err, code
    if user["role"] != "manager":
        return jsonify({"error": "Forbidden"}), 403
    db = get_db()
    profile = row_to_dict(db.execute("""
        SELECT u.id, u.email, u.full_name, u.phone, u.dob, u.address, u.profile_photo, u.account_status, u.created_at, p.account_number
        FROM users u LEFT JOIN profiles p ON p.user_id = u.id WHERE u.id = ?
    """, (user_id,)).fetchone())
    if not profile:
        db.close()
        return jsonify({"error": "Customer not found"}), 404
    loans = rows_to_list(db.execute("SELECT * FROM loan_applications WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall())
    txns = rows_to_list(db.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall())
    emis = rows_to_list(db.execute("SELECT * FROM emi_schedules WHERE user_id=? ORDER BY due_date ASC", (user_id,)).fetchall())
    db.close()
    return jsonify({"profile": profile, "loans": loans, "transactions": txns, "emis": emis})

# ─────────────────────────────────────────────
# LOAN APPLICATIONS
# ─────────────────────────────────────────────
@app.route("/api/loan-applications", methods=["GET"])
def get_applications():
    user, err, code = require_auth(request)
    if err: return err, code
    db = get_db()
    if user["role"] == "manager":
        apps = rows_to_list(db.execute("SELECT la.*, u.profile_photo FROM loan_applications la JOIN users u ON u.id = la.user_id ORDER BY la.created_at DESC").fetchall())
    else:
        apps = rows_to_list(db.execute("SELECT la.*, u.profile_photo FROM loan_applications la JOIN users u ON u.id = la.user_id WHERE la.user_id=? ORDER BY la.created_at DESC", (user["id"],)).fetchall())
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
        INSERT INTO loan_applications (id, user_id, applicant_name, no_of_dependents, education, self_employed, income_annum, loan_amount, loan_term, cibil_score, emi_day, monthly_emi, residential_assets_value, commercial_assets_value, luxury_assets_value, bank_asset_value, prediction_status, confidence, probability_of_default, risk_score, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (app_id, user["id"], body.get("applicant_name", user["full_name"]), body.get("no_of_dependents"), body.get("education"), body.get("self_employed"), body.get("income_annum"), body.get("loan_amount"), body.get("loan_term"), body.get("cibil_score"), body.get("emi_day", 5), body.get("monthly_emi", 0), body.get("residential_assets_value"), body.get("commercial_assets_value"), body.get("luxury_assets_value"), body.get("bank_asset_value"), body.get("prediction_status"), body.get("confidence"), body.get("probability_of_default"), body.get("risk_score"), "pending"))
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
    cur_app = db.execute("SELECT * FROM loan_applications WHERE id=?", (app_id,)).fetchone()
    if not cur_app:
        db.close()
        return jsonify({"error": "Application not found"}), 404
    old_status = cur_app["status"]
    db.execute("UPDATE loan_applications SET status=?, reviewed_at=? WHERE id=?", (status, datetime.utcnow().isoformat(), app_id))
    if status == "approved" and old_status != "approved":
        target_uid = cur_app["user_id"]
        amount = float(cur_app["loan_amount"])
        last_txn = db.execute("SELECT balance FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (target_uid,)).fetchone()
        cur_bal = float(last_txn["balance"]) if last_txn else 0
        db.execute("INSERT INTO transactions (id, user_id, type, amount, balance, description) VALUES (?,?,?,?,?,?)", (str(uuid.uuid4()), target_uid, "credit", amount, cur_bal + amount, f"Loan Disbursement: {app_id[:8].upper()}"))
        generate_emi_schedule(db, dict(cur_app))
    db.commit()
    db.close()
    return jsonify({"message": "Updated"})

# ─────────────────────────────────────────────
# TRANSACTIONS & DASHBOARD
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
    if user["role"] != "manager": return jsonify({"error": "Forbidden"}), 403
    body = request.json or {}
    target_uid = body.get("user_id")
    txn_type, amount = body.get("type"), float(body.get("amount", 0))
    db = get_db()
    last = db.execute("SELECT balance FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (target_uid,)).fetchone()
    bal = float(last["balance"]) if last else 0
    nb = bal + amount if txn_type == "credit" else bal - amount
    if txn_type == "debit" and nb < 0:
        db.close()
        return jsonify({"error": "Insufficient balance"}), 400
    tid = str(uuid.uuid4())
    db.execute("INSERT INTO transactions (id, user_id, type, amount, balance, description) VALUES (?,?,?,?,?,?)", (tid, target_uid, txn_type, amount, nb, body.get("description", "")))
    db.commit()
    db.close()
    return jsonify({"id": tid, "balance": nb}), 201

@app.route("/api/stats/manager", methods=["GET"])
def manager_stats():
    user, err, code = require_auth(request)
    if err: return err, code
    if user["role"] != "manager": return jsonify({"error": "Forbidden"}), 403
    db = get_db()
    stats = {
        "total_customers": db.execute("SELECT COUNT(*) as c FROM users WHERE role='customer'").fetchone()["c"],
        "pending_apps": db.execute("SELECT COUNT(*) as c FROM loan_applications WHERE status='pending'").fetchone()["c"],
        "approved_volume": db.execute("SELECT COALESCE(SUM(loan_amount),0) as s FROM loan_applications WHERE status='approved'").fetchone()["s"],
        "interest_earned": db.execute("SELECT COALESCE(SUM(amount),0) as s FROM emi_schedules WHERE status='paid'").fetchone()["s"],
        "pending_verifications": db.execute("SELECT COUNT(*) as c FROM users WHERE account_status='pending'").fetchone()["c"]
    }
    db.close()
    return jsonify(stats)

@app.route("/api/stats/manager/charts", methods=["GET"])
def manager_chart_stats():
    user, err, code = require_auth(request)
    if err: return err, code
    if user["role"] != "manager": return jsonify({"error": "Forbidden"}), 403
    db = get_db()
    status_counts = db.execute("SELECT status, COUNT(*) as count FROM loan_applications GROUP BY status").fetchall()
    monthly_loans = db.execute("SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count, SUM(loan_amount) as volume FROM loan_applications WHERE created_at >= date('now', '-6 months') GROUP BY month ORDER BY month ASC").fetchall()
    emi_perf = db.execute("SELECT status, COUNT(*) as count FROM emi_schedules GROUP BY status").fetchall()
    top_cust = db.execute("SELECT u.full_name, SUM(la.loan_amount) as total_loan FROM loan_applications la JOIN users u ON u.id = la.user_id WHERE la.status = 'approved' GROUP BY u.id ORDER BY total_loan DESC LIMIT 5").fetchall()
    db.close()
    return jsonify({
        "status_distribution": {row['status']: row['count'] for row in status_counts},
        "monthly_trends": [dict(row) for row in monthly_loans],
        "emi_performance": {row['status']: row['count'] for row in emi_perf},
        "top_customers": [dict(row) for row in top_cust]
    })

@app.route("/api/stats/customer", methods=["GET"])
def customer_stats():
    user, err, code = require_auth(request)
    if err: return err, code
    db = get_db()
    last = db.execute("SELECT balance FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user["id"],)).fetchone()
    res = {
        "balance": float(last["balance"]) if last else 0,
        "active_loans": db.execute("SELECT COUNT(*) as c FROM loan_applications WHERE user_id=? AND status='approved'", (user['id'],)).fetchone()["c"],
        "total_repaid": db.execute("SELECT COALESCE(SUM(paid_amount),0) as s FROM emi_schedules WHERE user_id=?", (user['id'],)).fetchone()["s"],
        "total_loan_amount": db.execute("SELECT COALESCE(SUM(loan_amount),0) as s FROM loan_applications WHERE user_id=? AND status='approved'", (user['id'],)).fetchone()["s"]
    }
    db.close()
    return jsonify(res)

# ─────────────────────────────────────────────
# ML & EMI ROUTES
# ─────────────────────────────────────────────
@app.route("/api/predict", methods=["POST"])
def predict_loan():
    user, err, code = require_auth(request)
    if err: return err, code
    try: return jsonify(ml_model.predict(request.json or {}))
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/ml/meta", methods=["GET"])
def ml_meta():
    user, err, code = require_auth(request)
    if err: return err, code
    if user["role"] != "manager": return jsonify({"error": "Forbidden"}), 403
    try: return jsonify(ml_model.get_model_meta())
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/emi/process", methods=["POST"])
def process_emis():
    user, err, code = require_auth(request)
    if err: return err, code
    db = get_db()
    res = process_emi_engine(db, None if user['role'] == 'manager' else user['id'])
    db.close()
    return jsonify(res)

@app.route("/api/emi/schedules")
def get_emi_schedules():
    user, err, code = require_auth(request)
    if err: return err, code
    db = get_db()
    q = "SELECT es.*, la.applicant_name FROM emi_schedules es JOIN loan_applications la ON la.id=es.loan_id"
    if user['role'] == 'manager':
        rows = db.execute(q + " ORDER BY es.due_date").fetchall()
    else:
        rows = db.execute(q + " WHERE es.user_id=? ORDER BY es.due_date", (user['id'],)).fetchall()
    db.close()
    return jsonify(rows_to_list(rows))

@app.route("/api/emi/settings/<loan_id>", methods=["GET", "POST"])
def emi_settings_route(loan_id):
    user, err, code = require_auth(request)
    if err: return err, code
    db = get_db()
    if request.method == "GET":
        row = db.execute("SELECT * FROM emi_settings WHERE loan_id=?", (loan_id,)).fetchone()
        db.close()
        return jsonify(row_to_dict(row) or {'auto_debit_enabled': 0})
    else:
        body = request.json or {}
        en = 1 if body.get('auto_debit_enabled') else 0
        existing = db.execute("SELECT id FROM emi_settings WHERE loan_id=?", (loan_id,)).fetchone()
        if existing: db.execute("UPDATE emi_settings SET auto_debit_enabled=? WHERE loan_id=?", (en, loan_id))
        else: db.execute("INSERT INTO emi_settings (id,loan_id,user_id,auto_debit_enabled) VALUES (?,?,?,?)", (str(uuid.uuid4()), loan_id, user['id'], en))
        db.commit(); db.close()
        return jsonify({'message': 'Updated'})

@app.route("/api/emi/pay/<emi_id>", methods=["POST"])
def pay_emi(emi_id):
    user, err, code = require_auth(request)
    if err: return err, code
    body = request.json or {}
    db = get_db()
    emi = row_to_dict(db.execute("SELECT * FROM emi_schedules WHERE id=?", (emi_id,)).fetchone())
    if not emi: db.close(); return jsonify({'error': 'EMI not found'}), 404
    if user['role'] != 'manager' and emi['user_id'] != user['id']: db.close(); return jsonify({'error': 'Forbidden'}), 403
    if user['role'] == 'customer' and body.get('mpin') != user['mpin']: db.close(); return jsonify({'error': 'Invalid MPIN'}), 401
    
    due = float(emi['amount']) + float(emi['late_fee'] or 0) - float(emi['paid_amount'] or 0)
    amt = float(body.get('amount', due))
    
    last = db.execute("SELECT balance FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (emi['user_id'],)).fetchone()
    bal = float(last['balance']) if last else 0
    if bal < amt:
        db.close()
        return jsonify({'error': f'Insufficient balance. Required: ₹{amt:,.2f}, Available: ₹{bal:,.2f}'}), 400
    
    # 1. Apply to current EMI
    apply_now = min(amt, due)
    new_paid = float(emi['paid_amount'] or 0) + apply_now
    new_status = 'paid' if new_paid >= float(emi['amount']) + float(emi['late_fee'] or 0) else 'partial'
    
    tid = str(uuid.uuid4())
    db.execute("UPDATE emi_schedules SET status=?, paid_amount=?, payment_mode='manual', transaction_id=?, paid_at=? WHERE id=?",
               (new_status, new_paid, tid, datetime.utcnow().isoformat(), emi_id))
    
    # 2. Handle Excess (Apply to future EMIs)
    excess = amt - apply_now
    covered_count = 0
    if excess > 0:
        future_emis = db.execute("SELECT * FROM emi_schedules WHERE loan_id=? AND status != 'paid' AND id != ? ORDER BY due_date ASC", (emi['loan_id'], emi_id)).fetchall()
        for f_emi in future_emis:
            if excess <= 0: break
            f_due = float(f_emi['amount']) + float(f_emi['late_fee'] or 0) - float(f_emi['paid_amount'] or 0)
            f_apply = min(excess, f_due)
            f_new_paid = float(f_emi['paid_amount'] or 0) + f_apply
            f_new_status = 'paid' if f_new_paid >= float(f_emi['amount']) + float(f_emi['late_fee'] or 0) else 'partial'
            
            db.execute("UPDATE emi_schedules SET status=?, paid_amount=?, payment_mode='manual_excess', transaction_id=?, paid_at=? WHERE id=?",
                       (f_new_status, f_new_paid, tid, datetime.utcnow().isoformat(), f_emi['id']))
            excess -= f_apply
            if f_new_status == 'paid': covered_count += 1

    # 3. Record Transaction
    desc = f"EMI Payment #{emi['emi_number']}"
    if covered_count > 0: desc += f" + Excess applied to {covered_count} future installments"
    db.execute("INSERT INTO transactions (id, user_id, type, amount, balance, description) VALUES (?,?,?,?,?,?)",
               (tid, emi['user_id'], 'debit', amt, bal - amt, desc))
    
    _notify(db, emi['user_id'], 'emi_paid', 'Excess Payment Applied', 
            f"Payment of ₹{amt:,.2f} processed. Current EMI settled and excess applied to future schedule.", emi['loan_id'], emi_id)
    
    db.commit()
    db.close()
    return jsonify({'message': 'Payment successful', 'balance': bal - amt, 'excess_applied_to': covered_count})

@app.route("/api/emi/summary")
def emi_summary():
    user, err, code = require_auth(request)
    if err: return err, code
    db = get_db(); uid = user['id']
    if user['role'] == 'manager':
        total = db.execute("SELECT COUNT(*) as c FROM emi_schedules WHERE status IN ('due_today','failed','overdue')").fetchone()['c']
        nxt = db.execute("SELECT * FROM emi_schedules WHERE status IN ('upcoming','due_today') ORDER BY due_date LIMIT 1").fetchone()
        out = db.execute("SELECT SUM(amount - paid_amount) as s FROM emi_schedules WHERE status != 'paid'").fetchone()['s'] or 0
    else:
        total = db.execute("SELECT COUNT(*) as c FROM emi_schedules WHERE user_id=? AND status IN ('due_today','failed','overdue')", (uid,)).fetchone()['c']
        nxt = db.execute("SELECT * FROM emi_schedules WHERE user_id=? AND status IN ('upcoming','due_today') ORDER BY due_date LIMIT 1", (uid,)).fetchone()
        out = db.execute("SELECT SUM(amount - paid_amount) as s FROM emi_schedules WHERE user_id=? AND status != 'paid'", (uid,)).fetchone()['s'] or 0
    
    last = db.execute("SELECT balance FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (uid,)).fetchone()
    db.close()
    return jsonify({'action_needed': total, 'next_emi': row_to_dict(nxt), 'balance': float(last['balance']) if last else 0, 'outstanding': float(out)})

@app.route("/api/notifications")
def get_notifications():
    user, err, code = require_auth(request)
    if err: return err, code
    db = get_db()
    rows = db.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (user['id'],)).fetchall()
    db.close()
    return jsonify(rows_to_list(rows))

@app.route("/api/notifications/<nid>", methods=["DELETE"])
def delete_notification(nid):
    user, err, code = require_auth(request)
    if err: return err, code
    db = get_db()
    db.execute("DELETE FROM notifications WHERE id=? AND user_id=?", (nid, user['id']))
    db.commit(); db.close()
    return jsonify({'message': 'Deleted'})

# ─────────────────────────────────────────────
# START
# ─────────────────────────────────────────────
@app.route("/")
def index(): return send_from_directory(FRONTEND_DIR, "auth.html")

@app.route("/<path:path>")
def static_files(path):
    if any(path.endswith(ext) for ext in [".html", ".js", ".css", ".png", ".jpg", ".svg", ".ico"]):
        return send_from_directory(FRONTEND_DIR, path)
    return jsonify({"error": "Not Found"}), 404

if __name__ == "__main__":
    init_db()
    PORT = 5001
    print(f"  ✅  Lendmark Server Started! http://localhost:{PORT}")
    app.run(debug=True, host="0.0.0.0", port=PORT)
