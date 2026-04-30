from flask import jsonify
from database import get_db

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
