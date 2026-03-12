"""AI reply suggestions for the unified inbox using Ollama.

Given a conversation thread and property context, generates a suggested
host reply using the configured Ollama model.
"""

from __future__ import annotations

import structlog

from app.config import PropertyConfig, get_config
from app.query.ollama_client import get_ollama_client

log = structlog.get_logger()

_SYSTEM_PROMPT_TPL = """\
You are a polite, professional vacation rental host named {host_name} managing {property_name}.

PROPERTY INFORMATION:
- Name: {property_name}
- Address: {address}
- Check-in time: {check_in_time}
- Check-out time: {check_out_time}
- WiFi password: {wifi_password}
- Lock code: {lock_code}
- Parking: {parking_instructions}

TASK:
Write a helpful, warm, concise reply to the latest guest message.

RULES:
1. Be friendly and professional.
2. Answer questions accurately using the property information above.
3. Keep the reply under 150 words unless the question warrants more detail.
4. Output only the message body — no salutation, no signature.
5. If you don't have the requested information, say so politely and offer to find out."""

_GENERIC_SYSTEM_PROMPT = (
    "You are a professional vacation rental host. "
    "Write a helpful, warm, concise reply to the guest's latest message. "
    "Output only the message body — no salutation, no signature. "
    "Keep it under 150 words."
)


async def generate_reply_suggestion(
    messages: list[dict],
    prop_cfg: PropertyConfig | None = None,
) -> str:
    """Generate an AI-suggested reply for a message thread.

    Args:
        messages: List of message dicts with keys: direction (inbound|outbound), body.
                  Should be in chronological order (oldest first).
        prop_cfg: Per-property configuration for context injection.

    Returns:
        Suggested reply text from Ollama.
    """
    config = get_config()
    client = get_ollama_client()

    if prop_cfg:
        system = _SYSTEM_PROMPT_TPL.format(
            host_name=prop_cfg.host_name or "Your host",
            property_name=prop_cfg.display_name,
            address=prop_cfg.address or "On file",
            check_in_time=prop_cfg.check_in_time,
            check_out_time=prop_cfg.check_out_time,
            wifi_password=prop_cfg.wifi_password or "See welcome message",
            lock_code=prop_cfg.lock_code or "See welcome message",
            parking_instructions=prop_cfg.parking_instructions or "None specific",
        )
    else:
        system = _GENERIC_SYSTEM_PROMPT

    ollama_messages: list[dict] = [{"role": "system", "content": system}]
    for msg in messages:
        role = "user" if msg["direction"] == "inbound" else "assistant"
        ollama_messages.append({"role": role, "content": msg["body"]})

    # If the thread ends with an outbound message, still request a fresh suggestion
    if not messages or messages[-1]["direction"] != "inbound":
        ollama_messages.append(
            {
                "role": "user",
                "content": "[Host requested a suggested reply for this conversation thread.]",
            }
        )

    response = await client.chat(
        model=config.ollama_model,
        messages=ollama_messages,
        options={"temperature": 0.7},
    )
    return response["message"]["content"].strip()
