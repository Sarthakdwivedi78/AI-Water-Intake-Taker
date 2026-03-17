import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Force load .env from project root (one level up from backend/)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

_llm = None


def _get_llm():
    global _llm
    if _llm is not None:
        return _llm

    api_key = os.getenv("GROQ_API_KEY", "").strip()

    print(f"[INFO] .env path     : {_ENV_PATH}")
    print(f"[INFO] .env exists   : {_ENV_PATH.exists()}")
    print(f"[INFO] GROQ_API_KEY  : {'SET (' + api_key[:8] + '...)' if api_key else 'NOT FOUND ❌'}")

    if not api_key:
        raise RuntimeError(
            f"GROQ_API_KEY not found in {_ENV_PATH}. "
            "Get a free key at https://console.groq.com"
        )

    model = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
    print(f"[INFO] Using model   : {model}")

    _llm = ChatGroq(
        groq_api_key=api_key,
        model_name=model,
        temperature=0.7,
    )
    return _llm


def get_ai_feedback(
    user_id: str,
    amount_ml: int,
    total_today_ml: int,
    daily_target_ml: int = 2000,
) -> str:
    """Call Groq LLM to get personalised hydration feedback."""
    pct       = round((total_today_ml / daily_target_ml) * 100, 1)
    remaining = max(daily_target_ml - total_today_ml, 0)

    prompt = (
        f"The user '{user_id}' just logged {amount_ml} ml of water. "
        f"Their total water intake today is {total_today_ml} ml. "
        f"Their personal daily target is {daily_target_ml} ml "
        f"(they have consumed {pct}% of their goal). "
        f"They still need {remaining} ml more to reach their target today. "
        f"Give a short, helpful, encouraging 2-3 sentence health tip about "
        f"their hydration progress. Be specific about percentage vs personal "
        f"target. Keep it friendly and motivating."
    )

    try:
        llm = _get_llm()
        response = llm.invoke(prompt)
        return response.content.strip()

    except RuntimeError as e:
        return f"⚠️ {e}"

    except Exception as e:
        error_text = str(e)
        print(f"[ERROR] Groq: {error_text}")
        if "401" in error_text or "invalid" in error_text.lower() or "authentication" in error_text.lower():
            return "⚠️ Invalid Groq API Key. Get a free key at https://console.groq.com"
        elif "429" in error_text or "rate" in error_text.lower():
            return "⚠️ Groq rate limit hit. Wait a moment and try again."
        elif "model" in error_text.lower() and "not found" in error_text.lower():
            return "⚠️ Model not found. Check GROQ_MODEL in .env"
        elif "connection" in error_text.lower() or "timeout" in error_text.lower():
            return "⚠️ Cannot reach Groq. Check your internet."
        else:
            return f"⚠️ AI error: {error_text}"
