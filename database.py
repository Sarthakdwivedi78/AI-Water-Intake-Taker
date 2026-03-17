from datetime import date, datetime
from pathlib import Path
import sqlite3
from threading import Lock

DB_PATH = Path(__file__).resolve().parent / "water_intake.db"
DB_LOCK = Lock()


def _get_connection() -> sqlite3.Connection:
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)


def init_db() -> None:
    with DB_LOCK:
        conn = _get_connection()
        try:
            # Water logs table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS water_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    amount_ml INTEGER NOT NULL,
                    logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    log_date TEXT NOT NULL
                )
                """
            )
            # Per-user daily target table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_targets (
                    user_id TEXT PRIMARY KEY,
                    daily_target_ml INTEGER NOT NULL DEFAULT 2000
                )
                """
            )
            conn.commit()
        finally:
            conn.close()


# ── Target helpers ───────────────────────────────────────────────────────────

def get_user_target(user_id: str) -> int:
    """Return the user's daily target in ml. Default 2000 ml."""
    with DB_LOCK:
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT daily_target_ml FROM user_targets WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return int(row[0]) if row else 2000
        finally:
            conn.close()


def set_user_target(user_id: str, target_ml: int) -> int:
    """Save or update the user's daily target. Returns the saved target."""
    if target_ml < 100:
        raise ValueError("Daily target must be at least 100 ml.")
    if target_ml > 20000:
        raise ValueError("Daily target cannot exceed 20,000 ml.")
    with DB_LOCK:
        conn = _get_connection()
        try:
            conn.execute(
                """
                INSERT INTO user_targets (user_id, daily_target_ml)
                VALUES (?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET daily_target_ml = excluded.daily_target_ml
                """,
                (user_id, target_ml),
            )
            conn.commit()
            return target_ml
        finally:
            conn.close()


# ── Water log helpers ────────────────────────────────────────────────────────

def log_water(user_id: str, amount: int) -> int:
    """Log water for a user. Returns today's total for that user."""
    amount = int(amount)
    if amount <= 0:
        raise ValueError("Water amount must be a positive number.")
    today = str(date.today())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with DB_LOCK:
        conn = _get_connection()
        try:
            conn.execute(
                "INSERT INTO water_logs (user_id, amount_ml, logged_at, log_date) VALUES (?, ?, ?, ?)",
                (user_id, amount, now, today),
            )
            conn.commit()
            row = conn.execute(
                "SELECT SUM(amount_ml) FROM water_logs WHERE user_id = ? AND log_date = ?",
                (user_id, today),
            ).fetchone()
            return int(row[0]) if row and row[0] else 0
        finally:
            conn.close()


def get_today_total(user_id: str) -> int:
    """Get today's total water intake for a user."""
    today = str(date.today())
    with DB_LOCK:
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT SUM(amount_ml) FROM water_logs WHERE user_id = ? AND log_date = ?",
                (user_id, today),
            ).fetchone()
            return int(row[0]) if row and row[0] else 0
        finally:
            conn.close()


def get_history(user_id: str) -> list:
    """Get all daily totals for a user (grouped by date)."""
    with DB_LOCK:
        conn = _get_connection()
        try:
            rows = conn.execute(
                """
                SELECT log_date, SUM(amount_ml) as total
                FROM water_logs
                WHERE user_id = ?
                GROUP BY log_date
                ORDER BY log_date DESC
                """,
                (user_id,),
            ).fetchall()
            return [{"date": row[0], "total_ml": int(row[1])} for row in rows]
        finally:
            conn.close()


def get_all_logs(user_id: str) -> list:
    """Get every individual log entry for a user."""
    with DB_LOCK:
        conn = _get_connection()
        try:
            rows = conn.execute(
                """
                SELECT logged_at, amount_ml, log_date
                FROM water_logs
                WHERE user_id = ?
                ORDER BY logged_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [{"logged_at": row[0], "amount_ml": int(row[1]), "log_date": row[2]} for row in rows]
        finally:
            conn.close()


init_db()
