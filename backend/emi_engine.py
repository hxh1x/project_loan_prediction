import uuid
from datetime import datetime, date, timedelta
import calendar
from database import get_db

def get_emi_date(base, emi_day, months_ahead):
    m = base.month + months_ahead
    y = base.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    d = min(emi_day, calendar.monthrange(y, m)[1])
    return date(y, m, d).isoformat()

def _notify(db, uid, ntype, title, msg, loan_id=None, emi_id=None):
    db.execute("INSERT INTO notifications (id,user_id,type,title,message,loan_id,emi_id) VALUES (?,?,?,?,?,?,?)",
              (str(uuid.uuid4()), uid, ntype, title, msg, loan_id, emi_id))

def generate_emi_schedule(db, loan_app):
    loan_id = loan_app["id"]
    user_id = loan_app["user_id"]
    term = int(loan_app["loan_term"] or 12)
    emi_amt = float(loan_app["monthly_emi"] or 0)
    emi_day = int(loan_app["emi_day"] or 5)
    if emi_amt <= 0:
        return
    existing = db.execute("SELECT id FROM emi_schedules WHERE loan_id=? LIMIT 1", (loan_id,)).fetchone()
    if existing:
        return
    today = date.today()
    for i in range(1, term + 1):
        due = get_emi_date(today, emi_day, i)
        db.execute(
            "INSERT INTO emi_schedules (id,loan_id,user_id,emi_number,amount,due_date) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), loan_id, user_id, i, emi_amt, due)
        )
    db.execute(
        "INSERT INTO emi_settings (id,loan_id,user_id,auto_debit_enabled) VALUES (?,?,?,1)",
        (str(uuid.uuid4()), loan_id, user_id)
    )
    _notify(db, user_id, "emi_reminder", "EMI Schedule Created",
            f"{term} monthly EMIs of ₹{emi_amt:,.0f} generated. First due: {get_emi_date(today, emi_day, 1)}", loan_id)

def process_emi_engine(db, user_id=None):
    today_str = date.today().isoformat()
    grace = (date.today() - timedelta(days=3)).isoformat()
    uf = "AND es.user_id=?" if user_id else ""
    uf_plain = "AND user_id=?" if user_id else ""
    up = (user_id,) if user_id else ()
    
    # Mark due_today
    uf_sched = "AND user_id=?" if user_id else ""
    db.execute(f"UPDATE emi_schedules SET status='due_today' WHERE status='upcoming' AND due_date<=? {uf_sched}", (today_str,)+up)
    
    # Mark overdue past grace period
    overdue_rows = db.execute(f"SELECT * FROM emi_schedules WHERE status IN ('due_today','failed') AND due_date<? {uf_sched}", (grace,)+up).fetchall()
    for e in overdue_rows:
        fee = round(float(e['amount']) * 0.02, 2)
        db.execute("UPDATE emi_schedules SET status='overdue', late_fee=? WHERE id=? AND status!='overdue'", (fee, e['id']))
    
    # Process auto-debits
    due = db.execute(f"""SELECT es.* FROM emi_schedules es
        JOIN emi_settings et ON et.loan_id=es.loan_id
        WHERE es.status IN ('due_today','failed','overdue') AND et.auto_debit_enabled=1 AND es.retry_count<3 {uf}""", up).fetchall()
    
    paid_c = failed_c = 0
    for e in due:
        already_paid_today = db.execute(
            "SELECT id FROM transactions WHERE user_id=? AND description=? AND date(created_at)=?",
            (e['user_id'], f"Monthly EMI Auto Debit #{e['emi_number']}", today_str)
        ).fetchone()
        if already_paid_today:
            continue
        rem = float(e['amount']) + float(e['late_fee'] or 0) - float(e['paid_amount'] or 0)
        if rem <= 0:
            continue
        last = db.execute("SELECT balance FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (e['user_id'],)).fetchone()
        bal = float(last['balance']) if last else 0
        if bal >= rem:
            nb = bal - rem
            tid = str(uuid.uuid4())
            db.execute("INSERT INTO transactions (id,user_id,type,amount,balance,description) VALUES (?,?,?,?,?,?)",
                       (tid, e['user_id'], 'debit', rem, nb, f"Monthly EMI Auto Debit #{e['emi_number']}"))
            db.execute("UPDATE emi_schedules SET status='paid',paid_amount=?,payment_mode='auto_debit',transaction_id=?,paid_at=? WHERE id=?",
                       (rem, tid, datetime.utcnow().isoformat(), e['id']))
            _notify(db, e['user_id'], 'emi_paid', 'EMI Paid', f"EMI #{e['emi_number']} ₹{rem:,.0f} auto-debited successfully.", e['loan_id'], e['id'])
            paid_c += 1
        else:
            db.execute("UPDATE emi_schedules SET status='failed',retry_count=retry_count+1 WHERE id=?", (e['id'],))
            _notify(db, e['user_id'], 'emi_failed', 'EMI Debit Failed',
                    f"Auto debit failed for EMI #{e['emi_number']}. Balance ₹{bal:,.0f}, needed ₹{rem:,.0f}. Please pay manually.", e['loan_id'], e['id'])
            failed_c += 1
            
    # Upcoming reminders
    for days, lbl in [(7,'7 days'),(3,'3 days'),(1,'tomorrow')]:
        rd = (date.today() + timedelta(days=days)).isoformat()
        upcoming = db.execute(f"SELECT * FROM emi_schedules WHERE status='upcoming' AND due_date=? {uf_sched}", (rd,)+up).fetchall()
        for e in upcoming:
            ex = db.execute("SELECT id FROM notifications WHERE emi_id=? AND type='emi_reminder' AND message LIKE ?",
                           (e['id'], f'%{lbl}%')).fetchone()
            if not ex:
                _notify(db, e['user_id'], 'emi_reminder', 'EMI Reminder',
                        f"EMI #{e['emi_number']} of ₹{e['amount']:,.0f} is due in {lbl} ({e['due_date']}).", e['loan_id'], e['id'])
                lb = db.execute("SELECT balance FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (e['user_id'],)).fetchone()
                if lb and float(lb['balance']) < float(e['amount']):
                    _notify(db, e['user_id'], 'low_balance', 'Low Balance Warning',
                            f"Your balance ₹{float(lb['balance']):,.0f} may not cover EMI ₹{e['amount']:,.0f} due in {lbl}.", e['loan_id'], e['id'])
    
    db.commit()
    return {'paid': paid_c, 'failed': failed_c}
