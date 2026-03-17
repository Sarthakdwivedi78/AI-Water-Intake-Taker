import os
import sqlite3
import streamlit as st
import pandas as pd
from datetime import date, datetime
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load .env for local development
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# ── Database setup ────────────────────────────────────────────────────────────
DB_PATH = Path("/tmp/water_intake.db") if os.path.exists("/tmp") else Path(__file__).parent / "water_intake.db"


def _conn():
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)


def init_db():
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS water_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            amount_ml INTEGER NOT NULL,
            logged_at TEXT NOT NULL,
            log_date TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_targets (
            user_id TEXT PRIMARY KEY,
            daily_target_ml INTEGER NOT NULL DEFAULT 2000
        )
    """)
    conn.commit()
    conn.close()


def log_water(user_id: str, amount: int) -> int:
    today = str(date.today())
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn  = _conn()
    conn.execute(
        "INSERT INTO water_logs (user_id, amount_ml, logged_at, log_date) VALUES (?,?,?,?)",
        (user_id, amount, now, today),
    )
    conn.commit()
    row = conn.execute(
        "SELECT SUM(amount_ml) FROM water_logs WHERE user_id=? AND log_date=?",
        (user_id, today),
    ).fetchone()
    conn.close()
    return int(row[0]) if row and row[0] else 0


def get_today_total(user_id: str) -> int:
    today = str(date.today())
    conn  = _conn()
    row   = conn.execute(
        "SELECT SUM(amount_ml) FROM water_logs WHERE user_id=? AND log_date=?",
        (user_id, today),
    ).fetchone()
    conn.close()
    return int(row[0]) if row and row[0] else 0


def get_history(user_id: str) -> list:
    conn = _conn()
    rows = conn.execute(
        """SELECT log_date, SUM(amount_ml)
           FROM water_logs WHERE user_id=?
           GROUP BY log_date ORDER BY log_date DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [{"date": r[0], "total_ml": int(r[1])} for r in rows]


def get_user_target(user_id: str) -> int:
    conn = _conn()
    row  = conn.execute(
        "SELECT daily_target_ml FROM user_targets WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return int(row[0]) if row else 2000


def set_user_target(user_id: str, target_ml: int):
    conn = _conn()
    conn.execute(
        """INSERT INTO user_targets (user_id, daily_target_ml) VALUES (?,?)
           ON CONFLICT(user_id) DO UPDATE SET daily_target_ml=excluded.daily_target_ml""",
        (user_id, target_ml),
    )
    conn.commit()
    conn.close()


init_db()


# ── Groq AI feedback ──────────────────────────────────────────────────────────
_llm = None


def get_llm():
    global _llm
    if _llm:
        return _llm

    # 1. Try Streamlit secrets (Streamlit Cloud)
    api_key = ""
    model   = "mixtral-8x7b-32768"
    try:
        api_key = st.secrets.get("GROQ_API_KEY", "")
        model   = st.secrets.get("GROQ_MODEL", "mixtral-8x7b-32768")
    except Exception:
        pass

    # 2. Fall back to environment variables / .env (local)
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY", "")
    if not model:
        model = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY not found.\n"
            "• Local: add it to your .env file\n"
            "• Streamlit Cloud: add it in App Settings → Secrets"
        )

    _llm = ChatGroq(groq_api_key=api_key, model_name=model, temperature=0.7)
    return _llm


def get_ai_feedback(user_id, amount_ml, total_today_ml, daily_target_ml):
    pct       = round((total_today_ml / daily_target_ml) * 100, 1)
    remaining = max(daily_target_ml - total_today_ml, 0)
    prompt = (
        f"User '{user_id}' just logged {amount_ml} ml. Total today: {total_today_ml} ml. "
        f"Daily target: {daily_target_ml} ml ({pct}% done). Remaining: {remaining} ml. "
        f"Give a short 2-3 sentence encouraging health tip about their hydration. "
        f"Be specific about their % vs personal target. Keep it friendly."
    )
    try:
        return get_llm().invoke(prompt).content.strip()
    except RuntimeError as e:
        return f"⚠️ {e}"
    except Exception as e:
        err = str(e)
        if "401" in err or "invalid" in err.lower():
            return "⚠️ Invalid Groq API Key. Check your secrets or .env file."
        elif "429" in err or "rate" in err.lower():
            return "⚠️ Rate limit hit. Wait a moment and try again."
        else:
            return f"⚠️ AI error: {err}"


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="💧 AI Water Tracker", page_icon="💧", layout="wide")

# ── Session state defaults ────────────────────────────────────────────────────
for key, val in [
    ("logged_in", False),
    ("active_user", ""),
    ("daily_target", 2000),
    ("water_amount", 250),
    ("last_log", None),
]:
    if key not in st.session_state:
        st.session_state[key] = val


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("💧 Water Tracker")

    st.markdown("### 👤 User Login")
    user_id_input = st.text_input(
        "User ID",
        value=st.session_state.active_user or "user1",
        placeholder="Enter your username...",
    )

    if st.button("🔐 Login", use_container_width=True, type="primary"):
        uid = user_id_input.strip()
        if not uid:
            st.error("Please enter a User ID.")
        else:
            st.session_state.logged_in    = True
            st.session_state.active_user  = uid
            st.session_state.daily_target = get_user_target(uid)
            st.session_state.last_log     = None
            st.success(f"Welcome, **{uid}**! 👋")
            st.rerun()

    if st.session_state.logged_in:
        st.caption(f"✅ Logged in as: **{st.session_state.active_user}**")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in   = False
            st.session_state.active_user = ""
            st.session_state.last_log    = None
            st.rerun()

    if st.session_state.logged_in:
        user_id = st.session_state.active_user

        st.markdown("---")
        st.markdown("### 🎯 Daily Target")

        new_target = st.number_input(
            "Set your daily goal (ml)",
            min_value=100, max_value=10000,
            value=st.session_state.daily_target,
            step=100,
            help="Recommended: 2000 ml per day",
        )

        if st.button("💾 Save Target", use_container_width=True):
            set_user_target(user_id, int(new_target))
            st.session_state.daily_target = int(new_target)
            st.success(f"Target saved: {new_target} ml ✅")

        st.markdown("**Quick presets:**")
        pc1, pc2, pc3 = st.columns(3)
        for col, label, val in [(pc1, "1.5L", 1500), (pc2, "2L", 2000), (pc3, "3L", 3000)]:
            if col.button(label, use_container_width=True):
                set_user_target(user_id, val)
                st.session_state.daily_target = val
                st.success(f"Target set to {val} ml ✅")
                st.rerun()

        st.markdown("---")
        st.markdown("### 💧 Log Water Intake")
        st.markdown("**Water Intake (ml)**")

        col_minus, col_val, col_plus = st.columns([1, 2, 1])
        with col_minus:
            if st.button("−", use_container_width=True):
                if st.session_state.water_amount > 50:
                    st.session_state.water_amount -= 50
        with col_val:
            st.session_state.water_amount = st.number_input(
                "", min_value=50, max_value=5000,
                value=st.session_state.water_amount,
                step=50, label_visibility="collapsed",
            )
        with col_plus:
            if st.button("+", use_container_width=True):
                st.session_state.water_amount += 50

        st.markdown("")
        submit = st.button("Submit", use_container_width=True, type="primary")
    else:
        submit = False
        user_id = ""


# ── Main dashboard ────────────────────────────────────────────────────────────
st.title("💧 AI Water Tracker Dashboard")

if not st.session_state.logged_in:
    st.markdown("---")
    st.markdown("""
## 👋 Welcome!
Please **enter your User ID** in the sidebar and click **🔐 Login** to get started.

### What you can do:
- 💧 Log your daily water intake
- 🎯 Set a personal daily hydration target
- 🤖 Get AI-powered health feedback after each log
- 📈 View your intake history and progress charts
    """)
    st.stop()

DAILY_GOAL_ML = st.session_state.daily_target

# ── Handle submit ─────────────────────────────────────────────────────────────
if submit:
    with st.spinner("Logging and getting AI feedback..."):
        try:
            total_today = log_water(user_id, int(st.session_state.water_amount))
            target      = get_user_target(user_id)
            ai_feedback = get_ai_feedback(user_id, st.session_state.water_amount, total_today, target)
            st.session_state.last_log = {
                "user_id":         user_id,
                "logged_ml":       st.session_state.water_amount,
                "total_today_ml":  total_today,
                "daily_target_ml": target,
                "ai_feedback":     ai_feedback,
            }
            st.session_state.daily_target = target
            DAILY_GOAL_ML = target
        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.stop()

# ── Show last log result ───────────────────────────────────────────────────────
if st.session_state.last_log:
    data        = st.session_state.last_log
    logged_ml   = data["logged_ml"]
    total_today = data["total_today_ml"]
    ai_feedback = data["ai_feedback"]
    goal        = data["daily_target_ml"]

    st.success(f"✅ Logged {logged_ml} ml for **{user_id}**")
    if ai_feedback:
        st.info(f"🤖 **AI Feedback:** {ai_feedback}")

    st.markdown("---")

    pct       = min(round((total_today / goal) * 100, 1), 100)
    remaining = max(goal - total_today, 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💧 Today's Total", f"{total_today} ml")
    c2.metric("🎯 Daily Target",  f"{goal} ml")
    c3.metric("📊 Progress",      f"{pct}%")
    c4.metric("⏳ Remaining",     f"{remaining} ml")

    st.progress(pct / 100)

    if total_today >= goal:
        st.balloons()
        st.success("🎉 Amazing! You've hit your daily target!")
    elif pct >= 75:
        st.warning(f"💪 Almost there! Just {remaining} ml more to go!")
    elif pct >= 50:
        st.warning(f"🌊 Halfway there! {remaining} ml left.")
    elif pct >= 25:
        st.info(f"📈 Good start! {remaining} ml remaining.")
    else:
        st.info(f"🚰 Just started! {remaining} ml to go today.")

    st.markdown("---")

# ── History section ───────────────────────────────────────────────────────────
st.subheader("📈 Water Intake History")

history = get_history(user_id)
target_for_chart = get_user_target(user_id)

if history:
    df = pd.DataFrame(history)
    df.columns = ["Date", "Water Intake (ml)"]
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")
    df["Goal Met?"] = df["Water Intake (ml)"].apply(
        lambda x: "✅ Yes" if x >= target_for_chart else "❌ No"
    )

    st.dataframe(df.reset_index(drop=True), use_container_width=True)

    st.markdown("**Daily Intake vs Target**")
    chart_df = df.set_index("Date")[["Water Intake (ml)"]].copy()
    chart_df["Daily Target (ml)"] = target_for_chart
    st.line_chart(chart_df)

    st.markdown("**Daily Intake Bar Chart**")
    st.bar_chart(df.set_index("Date")["Water Intake (ml)"])

    st.markdown("---")
    st.markdown("**📊 Summary Statistics**")
    avg        = int(df["Water Intake (ml)"].mean())
    best       = int(df["Water Intake (ml)"].max())
    days_met   = int((df["Water Intake (ml)"] >= target_for_chart).sum())
    total_days = len(df)

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("📅 Days Tracked",    total_days)
    s2.metric("💧 Avg Daily Intake", f"{avg} ml",
              delta=f"{avg - target_for_chart:+d} ml vs target")
    s3.metric("🏆 Best Day",         f"{best} ml")
    s4.metric("✅ Goal Hit",         f"{days_met}/{total_days} days")
else:
    st.info("No history yet. Log your first water intake using the sidebar!")
