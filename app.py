import streamlit as st
import requests
import pandas as pd

# ── Config ───────────────────────────────────────────────────────────────────
BACKEND = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI Water Tracker Dashboard",
    page_icon="💧",
    layout="wide",
)


# ── Helper: fetch current target from backend ─────────────────────────────
def fetch_target(uid: str) -> int:
    try:
        res = requests.post(f"{BACKEND}/get-target", json={"user_id": uid}, timeout=5)
        res.raise_for_status()
        return res.json().get("daily_target_ml", 2000)
    except Exception:
        return 2000


# ── Session state defaults ────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "active_user" not in st.session_state:
    st.session_state.active_user = ""
if "daily_target" not in st.session_state:
    st.session_state.daily_target = 2000
if "water_amount" not in st.session_state:
    st.session_state.water_amount = 250


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("💧 Water Tracker")

    # ── User ID + Login ───────────────────────────────────────────────────
    st.markdown("### 👤 User Login")
    user_id_input = st.text_input(
        "User ID",
        value=st.session_state.active_user or "user1",
        placeholder="Enter your username...",
    )

    login_clicked = st.button("🔐 Login", use_container_width=True, type="primary")

    if login_clicked:
        uid = user_id_input.strip()
        if not uid:
            st.error("Please enter a User ID.")
        else:
            # Log in — fetch their saved target
            st.session_state.logged_in  = True
            st.session_state.active_user = uid
            st.session_state.daily_target = fetch_target(uid)
            st.session_state.last_log = None   # clear previous log view
            st.success(f"Welcome, **{uid}**! 👋")
            st.rerun()

    # Show logout if logged in
    if st.session_state.logged_in:
        st.caption(f"✅ Logged in as: **{st.session_state.active_user}**")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in   = False
            st.session_state.active_user = ""
            st.session_state.last_log    = None
            st.rerun()

    # ── Only show the rest of the sidebar after login ─────────────────────
    if st.session_state.logged_in:
        user_id = st.session_state.active_user

        st.markdown("---")

        # ── Daily Target Section ──────────────────────────────────────────
        st.markdown("### 🎯 Daily Target")

        new_target = st.number_input(
            "Set your daily goal (ml)",
            min_value=100,
            max_value=10000,
            value=st.session_state.daily_target,
            step=100,
            help="Recommended: 2000 ml (2 litres) per day",
        )

        if st.button("💾 Save Target", use_container_width=True):
            try:
                res = requests.post(
                    f"{BACKEND}/set-target",
                    json={"user_id": user_id, "daily_target_ml": int(new_target)},
                    timeout=10,
                )
                res.raise_for_status()
                st.session_state.daily_target = int(new_target)
                st.success(f"Target saved: {new_target} ml ✅")
            except requests.exceptions.ConnectionError:
                st.error("❌ Backend not running.")
            except Exception as e:
                st.error(f"Error: {e}")

        # Quick preset buttons
        st.markdown("**Quick presets:**")
        pc1, pc2, pc3 = st.columns(3)
        for col, label, val in [(pc1, "1.5L", 1500), (pc2, "2L", 2000), (pc3, "3L", 3000)]:
            if col.button(label, use_container_width=True):
                try:
                    res = requests.post(
                        f"{BACKEND}/set-target",
                        json={"user_id": user_id, "daily_target_ml": val},
                        timeout=10,
                    )
                    res.raise_for_status()
                    st.session_state.daily_target = val
                    st.success(f"Target set to {val} ml ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("---")

        # ── Log Water Section ─────────────────────────────────────────────
        st.markdown("### 💧 Log Water Intake")
        st.markdown("**Water Intake (ml)**")

        col_minus, col_val, col_plus = st.columns([1, 2, 1])
        with col_minus:
            if st.button("−", use_container_width=True):
                if st.session_state.water_amount > 50:
                    st.session_state.water_amount -= 50
        with col_val:
            st.session_state.water_amount = st.number_input(
                "",
                min_value=50,
                max_value=5000,
                value=st.session_state.water_amount,
                step=50,
                label_visibility="collapsed",
            )
        with col_plus:
            if st.button("+", use_container_width=True):
                st.session_state.water_amount += 50

        st.markdown("")
        submit = st.button("Submit", use_container_width=True, type="primary")

    else:
        submit = False
        user_id = ""


# ── Main Dashboard ────────────────────────────────────────────────────────────
st.title("💧 AI Water Tracker Dashboard")

# ── Not logged in — show welcome screen ──────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown("---")
    st.markdown(
        """
        ## 👋 Welcome!
        Please **enter your User ID** in the sidebar and click **🔐 Login** to get started.

        ### What you can do:
        - 💧 Log your daily water intake
        - 🎯 Set a personal daily hydration target
        - 🤖 Get AI-powered health feedback after each log
        - 📈 View your intake history and progress charts
        """
    )
    st.stop()

# ── Logged in ─────────────────────────────────────────────────────────────────
DAILY_GOAL_ML = st.session_state.daily_target

# ── Handle Submit ──────────────────────────────────────────────────────────────
if submit:
    with st.spinner("Logging and getting AI feedback..."):
        try:
            res = requests.post(
                f"{BACKEND}/log",
                json={
                    "user_id": user_id,
                    "amount_ml": int(st.session_state.water_amount),
                },
                timeout=30,
            )
            res.raise_for_status()
            data = res.json()
            st.session_state.daily_target = data.get("daily_target_ml", DAILY_GOAL_ML)
            DAILY_GOAL_ML = st.session_state.daily_target
            st.session_state["last_log"] = data
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to backend. Run: `uvicorn backend.main:app --reload`")
            st.stop()
        except requests.exceptions.Timeout:
            st.error("⏱️ Request timed out. Try again.")
            st.stop()
        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.stop()

# ── Show Last Log Result ───────────────────────────────────────────────────────
if st.session_state.get("last_log"):
    data        = st.session_state["last_log"]
    logged_ml   = data.get("logged_ml", 0)
    total_today = data.get("total_today_ml", 0)
    ai_feedback = data.get("ai_feedback", "")
    uid         = data.get("user_id", user_id)
    goal        = data.get("daily_target_ml", DAILY_GOAL_ML)

    st.success(f"✅ Logged {logged_ml} ml for **{uid}**")

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
        st.warning(f"💪 Almost there! Just {remaining} ml more to reach your {goal} ml goal!")
    elif pct >= 50:
        st.warning(f"🌊 Halfway there! {remaining} ml left to hit your {goal} ml target.")
    elif pct >= 25:
        st.info(f"📈 Good start! Keep going — {remaining} ml remaining.")
    else:
        st.info(f"🚰 Just started! You need {remaining} ml more today.")

    st.markdown("---")

# ── History Section ────────────────────────────────────────────────────────────
st.subheader("📈 Water Intake History")

try:
    res = requests.post(
        f"{BACKEND}/history",
        json={"user_id": user_id},
        timeout=10,
    )
    res.raise_for_status()
    payload         = res.json()
    history         = payload.get("history", [])
    target_from_api = payload.get("daily_target_ml", DAILY_GOAL_ML)

    if history:
        df = pd.DataFrame(history)
        df.columns = ["Date", "Water Intake (ml)"]
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")
        df["Goal Met?"] = df["Water Intake (ml)"].apply(
            lambda x: "✅ Yes" if x >= target_from_api else "❌ No"
        )

        st.dataframe(df.reset_index(drop=True), use_container_width=True)

        st.markdown("**Daily Intake vs Target**")
        chart_df = df.set_index("Date")[["Water Intake (ml)"]].copy()
        chart_df["Daily Target (ml)"] = target_from_api
        st.line_chart(chart_df)

        st.markdown("**Daily Intake Bar Chart**")
        st.bar_chart(df.set_index("Date")["Water Intake (ml)"])

        st.markdown("---")
        st.markdown("**📊 Summary Statistics**")
        avg       = int(df["Water Intake (ml)"].mean())
        best      = int(df["Water Intake (ml)"].max())
        days_met  = int((df["Water Intake (ml)"] >= target_from_api).sum())
        total_days = len(df)

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("📅 Days Tracked",     total_days)
        s2.metric("💧 Avg Daily Intake",  f"{avg} ml",
                  delta=f"{avg - target_from_api:+d} ml vs target")
        s3.metric("🏆 Best Day",          f"{best} ml")
        s4.metric("✅ Goal Hit",          f"{days_met}/{total_days} days")

    else:
        st.info("No history yet. Log your first water intake using the sidebar!")

except requests.exceptions.ConnectionError:
    st.warning("⚠️ Start the backend to see history.")
except Exception as e:
    st.error(f"Could not load history: {e}")
