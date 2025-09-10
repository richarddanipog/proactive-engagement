import re
import json
from typing import Optional, Tuple, Dict, Any
from openai import OpenAI
from .settings import settings
from .schemas import SessionSnapshot
from .logger import logger


def extract_session_insights(session: SessionSnapshot) -> Dict[str, Any]:
    """Extract meaningful insights from session events."""
    insights = {
        "page_views": [],
        "interactions": [],
        "dwell_patterns": [],
        "journey": [],
        "behavioral_signals": {}
    }

    # Process events
    for event in session.events:
        page = event.page
        meta = event.meta
        timestamp = event.timestamp

        match event.type:
            case "page_view":
                insights["page_views"].append({
                    "page": page,
                    "path": meta.get("path", ""),
                    "timestamp": timestamp
                })
                insights["journey"].append(f"viewed_{page}")

            case "click":
                action = meta.get("action", "")
                insights["interactions"].append({
                    "action": action,
                    "page": page,
                    "quantity": meta.get("quantity"),
                    "timestamp": timestamp
                })
                insights["journey"].append(f"{action}_on_{page}")

            case "dwell_tick":
                insights["dwell_patterns"].append({
                    "page": page,
                    "elapsed_sec": meta.get("elapsed_sec", 0),
                    "timestamp": timestamp
                })

    # Calculate behavioral signals
    signals = insights["behavioral_signals"]

    # Engagement level
    total_interactions = len(insights["interactions"])
    add_to_cart_count = sum(
        1 for i in insights["interactions"] if i["action"] == "add_to_cart")
    qty_changes = sum(
        1 for i in insights["interactions"] if "qty" in i["action"])

    signals["engagement_level"] = (
        "high" if total_interactions >= 3 else
        "medium" if total_interactions >= 1 else
        "low"
    )

    # Intent signals
    signals["purchase_intent"] = (
        "high" if add_to_cart_count > 0 else
        "medium" if qty_changes > 0 or session.current_page == "cart" else
        "exploring" if len(insights["page_views"]) > 1 else
        "low"
    )

    # Browse pattern
    unique_pages = len(set(pv["page"] for pv in insights["page_views"]))
    signals["browse_pattern"] = (
        "focused" if unique_pages == 1 else
        "exploring" if unique_pages <= 3 else
        "browsing_widely"
    )

    # Time investment
    signals["time_investment"] = (
        "high" if session.time_on_site >= 120 else
        "medium" if session.time_on_site >= 30 else
        "low"
    )

    # Cart abandonment risk
    if session.cart_items > 0 and session.current_page != "cart":
        signals["abandonment_risk"] = "high"
    elif add_to_cart_count > 0 and session.current_page == "product":
        signals["abandonment_risk"] = "medium"
    else:
        signals["abandonment_risk"] = "low"

    return insights


def create_enhanced_payload(session: SessionSnapshot) -> Dict[str, Any]:
    """Create enhanced payload with behavioral insights."""
    insights = extract_session_insights(session)

    return {
        "current_page": session.current_page,
        "cart_items": session.cart_items,
        "time_on_site_sec": session.time_on_site,
        "total_events": len(session.events),
        "page_views_count": len(insights["page_views"]),
        "interactions_count": len(insights["interactions"]),
        "journey": insights["journey"][-5:],  # Last 5 actions
        "behavioral_signals": insights["behavioral_signals"],
        "recent_actions": [
            {
                "type": event.type,
                "action": event.meta.get("action"),
                "page": event.page
            }
            for event in session.events[-3:]  # Last 3 events
            if event.type in ["click", "page_view"]
        ]
    }


def analyze_session_with_openai(session: SessionSnapshot) -> Tuple[bool, Optional[str], int]:
    """
    Returns (should_show, message, ttl_seconds).
    Enhanced with behavioral analysis from session events.
    """
    logger.info('Analyze session as started.')
    if not settings.openai_api_key:
        logger.warning(
            "OpenAI API key not found. Please set OPENAI_API_KEY in your environment variables.")
        return (False, None, 0)

    client = OpenAI(api_key=settings.openai_api_key)

    system = (
        "You are a conversion optimization assistant for an e-commerce site. "
        "Analyze the session data including user journey, behavioral signals, and interactions. "
        "Decide if showing a popup NOW would be helpful (not annoying) and craft a personalized message. "
        "Rules: "
        "- Only show popups for high-value moments (cart abandonment, extended browsing, purchase hesitation) "
        "- Message must be <= 120 chars, helpful tone, no emojis "
        "- Consider user's current context and journey stage "
        "- Avoid interrupting active shopping (recent add-to-cart or quantity changes) "
        "- TTL should be 60-120 seconds based on urgency"
    )

    payload = create_enhanced_payload(session)

    try:
        resp = client.chat.completions.create(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": (
                    "Analyze this session and return JSON with keys: should_show (boolean), message (string or null), ttl_seconds (integer). "
                    "Consider the user's behavioral signals and journey context. "
                    f"Session data: {json.dumps(payload, indent=2)}"
                )},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        logger.debug(f"Raw LLM response text: {text}")
        # Extract JSON from response
        block = re.search(r"\{.*\}", text, flags=re.S)
        if not block:
            return (False, None, 0)

        data = json.loads(block.group(0))

        return _process_data(data)
    except json.JSONDecodeError as e:
        # Fallback: try to extract just the boolean decision
        logger.error(f"Failed to parse LLM response as JSON. Error={e}")
        if "should_show" in text.lower() and ("true" in text.lower() or "false" in text.lower()):
            should_show = "true" in text.lower()
            return (should_show, None, 90 if should_show else 0)
        return (False, None, 0)
    except Exception as e:
        logger.error(f"LLM analysis failed with exception: {e}")
        return (False, None, 0)


def _process_data(data: dict) -> tuple[bool, str, int]:
    """
    Process banner data with validation and cleaning.
    Args:
        data: Dictionary containing banner configuration
    Returns:
        Tuple of (should_show, message, ttl_seconds)
    """
    should_show = bool(data.get("should_show", False))
    message = data.get("message", "")
    ttl = int(data.get("ttl_seconds", 90)) if should_show else 0

    # Clean and validate message
    if message:
        message = message.strip().strip('"\'')
        if len(message) > 120:
            message = message[:117] + "..."

    # Validate TTL range if banner should be shown
    if should_show and ttl > 0:
        ttl = max(30, min(180, ttl))

    return should_show, message, ttl
