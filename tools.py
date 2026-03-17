# tools.py — not used directly by main.py
# Kept for reference only

try:
    from backend.database import log_water, get_today_total
except ImportError:
    from database import log_water, get_today_total

_current_user_id = "default"

def set_user(user_id: str):
    global _current_user_id
    _current_user_id = user_id
