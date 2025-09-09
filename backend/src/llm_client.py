import re
import json
from typing import Optional, Tuple
from openai import OpenAI
from .settings import settings
from .schemas import SessionSnapshot


def analyze_session_with_openai(session: SessionSnapshot) -> Tuple[bool, Optional[str], int]:
    """
    Returns (should_show, message, ttl_seconds).
    """
    if not settings.openai_api_key:
        return (False, None, 0)

    client = OpenAI(api_key=settings.openai_api_key)

    system = (
        "You are a conversion assistant for a Shopify-like e-commerce site. "
        "Given a compact session summary, decide whether to show a popup NOW and, if yes, generate a concise message. "
        "Constraints: message <= 120 chars, neutral/helpful tone, no emojis."
    )

    payload = {
        "current_page": session.current_page,
        "cart_items": session.cart_items,
        "time_on_site_sec": session.time_on_site,
        "events_count": len(session.events),
    }

    try:
        resp = client.chat.completions.create(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": (
                    "Return JSON with keys: should_show (boolean), message (string or null), ttl_seconds (integer). "
                    f"Session: {payload}"
                )},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()

        block = re.search(r"\{.*\}", text, flags=re.S)
        data = json.loads(block.group(0)) if block else {}

        should_show = bool(data.get("should_show", False))
        message = data.get("message")
        ttl = int(data.get("ttl_seconds", 0)) if should_show else 0

        if message:
            message = message.strip()
            if len(message) > 120:
                message = message[:117] + "..."

        return (should_show, message, ttl)
    except Exception:
        return (False, None, 0)
