from typing import Optional
import os
import json
import requests
import pandas as pd
import config


def dataframe_to_context(df: pd.DataFrame, max_rows: int = 200) -> str:
    if df is None or df.empty:
        return "No Semgrep findings."
    limited = df.head(max_rows)
    return limited.to_csv(index=False)


def recommend_secure_fixes_rest(
    df: pd.DataFrame,
    user_question: Optional[str],
    model_name: Optional[str] = None,
    max_rows: int = 200,
) -> str:
    """
    Call Gemini API via REST (v1beta) using the endpoint pattern:
    https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
    """
    # Resolve API key from env first, then config as fallback
    api_key = os.getenv("GEMINI_API_KEY") or getattr(config, "GEMINI_API_KEY", None)
    if not api_key:
        raise RuntimeError("No GEMINI_API_KEY available in environment or config.")

    # Prefer provided model; default to 2.0 flash for broad availability
    model = model_name or getattr(config, "GEMINI_MODEL", None) or "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    context_csv = dataframe_to_context(df, max_rows=max_rows)
    question = user_question or "Provide secure coding recommendations to fix these findings."
    prompt = (
        "You are a senior application security engineer. Given static analysis findings in CSV, provide "
        "precise, language-appropriate secure coding recommendations with concise examples when useful. Be practical.\n\n"
        f"Findings (CSV):\n{context_csv}\n\nQuestion: {question}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key,
    }
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini REST error {resp.status_code}: {resp.text}")
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return json.dumps(data, indent=2)


def has_env_gemini_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or getattr(config, "GEMINI_API_KEY", None))
