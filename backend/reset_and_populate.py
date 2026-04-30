import sqlite3
import uuid
import hashlib
import random
import os
import requests
from datetime import datetime, timedelta, date
import calendar

# Setup paths relative to script in backend/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(ROOT_DIR, "data", "lendmark.db")
UPLOAD_FOLDER = os.path.join(ROOT_DIR, "data", "uploads")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Professional Photo IDs (Unsplash)
MALE_PHOTOS = ["photo-1566492031773-4f4e44671857", "photo-1507003211169-0a1dd7228f2d", "photo-1531384441138-2736e62e0919", "photo-1500648767791-00dcc994a43e", "photo-1472099645785-5658abf4ff4e", "photo-1519085360753-af0119f7cbe7"]
FEMALE_PHOTOS = ["photo-1573496359142-b8d87734a5a2", "photo-1573497019940-1c28c88b4f3e", "photo-1580489944761-15a19d654956", "photo-1567532939604-b6b5b0ad2f01", "photo-1494790108377-be9c29b29330"]

CUSTOMERS = [
    ("Rajesh Kumar", "rajesh.k@corporate.in", "male", "Tech Mahindra", "SVP Operations"),
    ("Sunita Deshmukh", "sunita.d@design.co", "female", "Studio D", "Lead Architect"),
    ("Amitav Ghosh", "amitav.g@writer.in", "male", "Deloitte", "Senior Consultant"),
    ("Deepika Rao", "deepika.r@finance.com", "female", "HDFC Bank", "Finance Director"),
    ("Sanjay Malhotra", "sanjay.m@it.net", "male", "Google India", "Principal Engineer"),
    ("Meera Nair", "meera.n@science.org", "female", "ISRO", "Senior Scientist"),
    ("Arjun Kapoor", "arjun.k@marketing.in", "male", "Unilever", "Marketing Manager"),
    ("Kavita Singh", "kavita.s@hr.com", "female", "Amazon", "HR Business Partner"),
    ("Vikram Rathore", "vikram.r@strategy.in", "male", "Reliance", "Head of Strategy"),
    ("Ananya Chatterjee", "ananya.c@product.co", "female", "Zomato", "Product Owner")
]

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def get_emi_date(base, emi_day, months_ahead):
    m = base.month + months_ahead
    y = base.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    d = min(emi_day, calendar.monthrange(y, m)[1])
    return date(y, m, d)

def reset_and_populate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Clearing existing customer data...")
    cursor.execute("DELETE FROM users WHERE role='customer'")
    cursor.execute("DELETE FROM profiles WHERE user_id NOT IN (SELECT id FROM users WHERE role='manager')")
    cursor.execute("DELETE FROM loan_applications")
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM emi_schedules")
    cursor.execute("DELETE FROM emi_settings")
    cursor.execute("DELETE FROM notifications")
    
    m_idx = 0
    f_idx = 0
    
    for name, email, gender, company, job in CUSTOMERS:
        uid = str(uuid.uuid4())
        phone = f"9845{random.randint(100000, 999999)}"
        dob = (date(1975, 1, 1) + timedelta(days=random.randint(0, 9000))).isoformat()
        address = f"Residence {random.randint(100, 999)}, Prestige Estate, Bangalore"
        
        # Photo
        photo_id = FEMALE_PHOTOS[f_idx % len(FEMALE_PHOTOS)] if gender == 'female' else MALE_PHOTOS[m_idx % len(MALE_PHOTOS)]
        if gender == 'female': f_idx += 1
        else: m_idx += 1
        
        photo_filename = f"{uid}_prof.jpg"
        try:
            url = f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w=300&h=300&q=80"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(os.path.join(UPLOAD_FOLDER, photo_filename), 'wb') as f: f.write(r.content)
        except: photo_filename = None

        # User & Profile
        cursor.execute("INSERT INTO users (id, email, password_hash, full_name, phone, dob, address, profile_photo, role, account_status) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (uid, email, hash_pw("password123"), name, phone, dob, address, photo_filename, "customer", "approved"))
        cursor.execute("INSERT INTO profiles (id, user_id, full_name, account_number) VALUES (?,?,?,?)",
                       (str(uuid.uuid4()), uid, name, "ACC" + uid[:8].upper()))
        
        # Loan
        loan_id = str(uuid.uuid4())
        amount = random.randint(5, 50) * 100000
        salary = random.randint(150000, 450000)
        term = random.choice([12, 24, 36])
        emi_day = 5
        monthly_emi = round((amount * 1.1) / term, 2)
        
        # Randomize Start Date (Between 30 and 180 days ago)
        days_ago = random.randint(30, 180)
        start_date_dt = datetime.now() - timedelta(days=days_ago)
        start_date = start_date_dt.date()
        
        # Realistic banking metrics
        cibil = random.randint(650, 850)
        prob_default = random.uniform(2, 15) if cibil > 750 else random.uniform(15, 35)
        risk_score = round(prob_default, 1)
        confidence = random.uniform(94, 99)

        cursor.execute("""INSERT INTO loan_applications 
            (id, user_id, applicant_name, income_annum, loan_amount, loan_term, emi_day, monthly_emi, status, prediction_status, confidence, cibil_score, probability_of_default, risk_score, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (loan_id, uid, name, salary*12, amount, term, emi_day, monthly_emi, "approved", "Approved", confidence, cibil, prob_default, risk_score, start_date_dt.isoformat()))
        
        # Strictly Loan/EMI Transactions
        current_balance = 0 
        # disbursement happens 2 days after application
        disbursed_dt = start_date_dt + timedelta(days=2, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        
        def add_txn(t_date, t_type, t_amount, t_desc):
            nonlocal current_balance
            if t_type == "credit": current_balance += t_amount
            else: current_balance -= t_amount
            cursor.execute("INSERT INTO transactions (id, user_id, type, amount, balance, description, created_at) VALUES (?,?,?,?,?,?,?)",
                           (str(uuid.uuid4()), uid, t_type, t_amount, current_balance, t_desc, t_date.strftime("%Y-%m-%d %H:%M:%S")))

        # 1. Loan Disbursement (The only Credit)
        add_txn(disbursed_dt, "credit", amount, f"Loan Disbursement: {loan_id[:8].upper()}")
        
        # 2. Add some paid EMIs (Debits)
        # Calculate how many EMIs have passed since start_date
        months_passed = (datetime.now().year - start_date.year) * 12 + (datetime.now().month - start_date.month)
        # We only mark them as paid if they were due in the past
        paid_count = min(months_passed, random.randint(1, 3)) if months_passed > 0 else 0
        
        for i in range(1, paid_count + 1):
            curr_date = get_emi_date(start_date, emi_day, i)
            # Add random time to EMI payment
            curr_dt = datetime.combine(curr_date, datetime.min.time()) + timedelta(hours=random.randint(9, 17), minutes=random.randint(0, 59))
            
            add_txn(curr_dt, "debit", monthly_emi, f"Manual EMI Payment #{i}")
            
            due_date_str = curr_date.isoformat()
            cursor.execute("INSERT INTO emi_schedules (id, loan_id, user_id, emi_number, amount, paid_amount, due_date, status, paid_at) VALUES (?,?,?,?,?,?,?,?,?)",
                           (str(uuid.uuid4()), loan_id, uid, i, monthly_emi, monthly_emi, due_date_str, 'paid', curr_dt.isoformat()))

        # 3. Add remaining EMIs (Upcoming)
        for i in range(paid_count + 1, term + 1):
            due = get_emi_date(start_date, emi_day, i)
            cursor.execute("INSERT INTO emi_schedules (id, loan_id, user_id, emi_number, amount, paid_amount, due_date, status) VALUES (?,?,?,?,?,?,?,?)",
                           (str(uuid.uuid4()), loan_id, uid, i, monthly_emi, 0, due.isoformat(), 'upcoming'))

    conn.commit()
    conn.close()
    print("Database reset! Strictly loan-related transactions only.")

if __name__ == "__main__":
    reset_and_populate()
