# 💧 AI Water Intake Tracker

An AI-powered daily water intake tracking app built with **FastAPI**, **Streamlit**, and **Groq (Mixtral LLM)**. Log your water intake, set personal daily targets, get real-time AI health feedback, and track your hydration history — all in one dashboard.

---

## 🚀 Features

- 🔐 **Multi-user login** — each user has their own data and settings
- 💧 **Log water intake** — with `+` / `−` controls in ml
- 🎯 **Personal daily target** — set and save your own hydration goal (quick presets: 1.5L, 2L, 3L)
- 🤖 **AI feedback** — real-time personalised health tips powered by Groq (Mixtral-8x7b)
- 📊 **Progress tracking** — progress bar, 4 live metrics, motivational messages
- 📈 **History dashboard** — daily table, intake vs target line chart, bar chart, summary stats
- 🗄️ **SQLite database** — persistent storage, auto daily reset, per-user data isolation

---

## 🗂️ Project Structure

```
water-intake-ai-agent/
│
├── backend/
│   ├── main.py        # FastAPI server & API endpoints
│   ├── agent.py       # Groq LLM integration for AI feedback
│   ├── database.py    # SQLite database — logs & user targets
│   ├── tools.py       # Helper tools
│   └── memory.py      # Memory module
│
├── frontend/
│   └── app.py         # Streamlit dashboard UI
│
├── requirements.txt
└── .env
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ai-water-intake-tracker.git
cd ai-water-intake-tracker
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Get a free Groq API key

1. Go to [https://console.groq.com](https://console.groq.com)
2. Sign up for free (no credit card needed)
3. Click **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

### 4. Configure your `.env` file

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_your_actual_key_here
GROQ_MODEL=mixtral-8x7b-32768
```

**Available free models:**

| Model | Speed | Quality |
|---|---|---|
| `mixtral-8x7b-32768` | Fast | ⭐ Best (recommended) |
| `llama3-8b-8192` | Fast | Good |
| `llama-3.1-8b-instant` | Fastest | Good |
| `gemma2-9b-it` | Fast | Good |

---

## ▶️ Running the App

Open **two terminals** from the project root:

**Terminal 1 — Start the backend:**
```bash
uvicorn backend.main:app --reload
```

**Terminal 2 — Start the frontend:**
```bash
streamlit run frontend/app.py
```

Then open your browser at **http://localhost:8501**

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/log` | Log water intake + get AI feedback |
| `POST` | `/today` | Get today's total for a user |
| `POST` | `/history` | Get full daily history |
| `POST` | `/set-target` | Set user's daily goal |
| `POST` | `/get-target` | Get user's current goal |

Interactive API docs available at: **http://127.0.0.1:8000/docs**

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| AI / LLM | Groq (Mixtral-8x7b) via LangChain |
| Database | SQLite |
| Language | Python 3.9+ |

---

## 📸 Screenshots

> Dashboard shows: login, water logging with +/− controls, AI feedback, progress metrics, history table and charts.

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 🙏 Acknowledgements

Built as part of the **Euron.one** AI Agent course project.
