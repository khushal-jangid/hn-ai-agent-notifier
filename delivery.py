"""Optional delivery hooks for scheduled AgentScout runs."""

from __future__ import annotations

import base64
import json
import os
import smtplib
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from typing import Any

GMAIL_REQUIRED_ENV = [
    "AGENTSCOUT_EMAIL_TO",
    "AGENTSCOUT_EMAIL_FROM",
    "AGENTSCOUT_GMAIL_CLIENT_ID",
    "AGENTSCOUT_GMAIL_CLIENT_SECRET",
    "AGENTSCOUT_GMAIL_REFRESH_TOKEN",
]


def send_brief(payload: dict[str, Any]) -> dict[str, Any]:
    """Send a rendered brief through SMTP, Gmail API, or a webhook."""

    delivery_mode = os.environ.get("AGENTSCOUT_DELIVERY", "auto").lower()
    if delivery_mode == "smtp" or _smtp_configured():
        return send_smtp(payload)
    if delivery_mode == "gmail":
        return send_gmail(payload)
    if delivery_mode == "webhook":
        return send_webhook(payload)
    if _gmail_configured():
        return send_gmail(payload)
    if os.environ.get("AGENTSCOUT_WEBHOOK_URL"):
        return send_webhook(payload)
    return {
        "configured": False,
        "sent": False,
        "status": "skipped_no_delivery",
        "detail": (
            "Set SMTP credentials, Gmail environment variables, or AGENTSCOUT_WEBHOOK_URL to deliver "
            "scheduled briefs."
        ),
    }


def _smtp_configured() -> bool:
    return bool(os.environ.get("AGENTSCOUT_EMAIL_TO") and os.environ.get("AGENTSCOUT_SMTP_PASSWORD"))


def send_smtp(payload: dict[str, Any]) -> dict[str, Any]:
    """Send brief using standard SMTP (Gmail/Outlook/Custom)."""
    to_email = os.environ.get("AGENTSCOUT_EMAIL_TO")
    from_email = os.environ.get("AGENTSCOUT_EMAIL_FROM") or to_email
    password = os.environ.get("AGENTSCOUT_SMTP_PASSWORD")
    host = os.environ.get("AGENTSCOUT_SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("AGENTSCOUT_SMTP_PORT", "465"))

    if not to_email or not password:
        return {
            "provider": "smtp",
            "configured": False,
            "sent": False,
            "status": "missing_credentials",
            "detail": "Requires AGENTSCOUT_EMAIL_TO and AGENTSCOUT_SMTP_PASSWORD"
        }

    try:
        msg = EmailMessage()
        msg["Subject"] = payload["subject"]
        msg["From"] = from_email
        msg["To"] = to_email
        msg.set_content(payload["text"])
        msg.add_alternative(payload["html"], subtype="html")

        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as server:
                server.login(from_email, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls()
                server.login(from_email, password)
                server.send_message(msg)

        return {
            "provider": "smtp",
            "configured": True,
            "sent": True,
            "status": "sent",
            "to": to_email
        }
    except Exception as exc:
        return {
            "provider": "smtp",
            "configured": True,
            "sent": False,
            "status": "error",
            "error": str(exc)
        }


def _gmail_configured() -> bool:
    return all(os.environ.get(name) for name in GMAIL_REQUIRED_ENV)


def _missing_gmail_config() -> list[str]:
    return [name for name in GMAIL_REQUIRED_ENV if not os.environ.get(name)]


def _fetch_gmail_access_token() -> str:
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=urllib.parse.urlencode(
            {
                "client_id": os.environ["AGENTSCOUT_GMAIL_CLIENT_ID"],
                "client_secret": os.environ["AGENTSCOUT_GMAIL_CLIENT_SECRET"],
                "refresh_token": os.environ["AGENTSCOUT_GMAIL_REFRESH_TOKEN"],
                "grant_type": "refresh_token",
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        token_payload = json.loads(response.read().decode("utf-8"))
    return str(token_payload["access_token"])


def send_gmail(payload: dict[str, Any]) -> dict[str, Any]:
    """Send the rendered brief through the Gmail API."""

    missing = _missing_gmail_config()
    if missing:
        return {
            "provider": "gmail",
            "configured": False,
            "sent": False,
            "status": "skipped_missing_gmail_config",
            "missing": missing,
        }

    try:
        access_token = _fetch_gmail_access_token()
        message = EmailMessage()
        message["To"] = os.environ["AGENTSCOUT_EMAIL_TO"]
        message["From"] = os.environ["AGENTSCOUT_EMAIL_FROM"]
        message["Subject"] = payload["subject"]
        message.set_content(payload["text"])
        message.add_alternative(payload["html"], subtype="html")

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        request = urllib.request.Request(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            data=json.dumps({"raw": encoded_message}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        return {
            "provider": "gmail",
            "configured": True,
            "sent": True,
            "status": "sent",
            "message_id": response_payload.get("id"),
            "thread_id": response_payload.get("threadId"),
        }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {
            "provider": "gmail",
            "configured": True,
            "sent": False,
            "status": exc.code,
            "error": detail[:500],
        }
    except (KeyError, urllib.error.URLError, TimeoutError) as exc:
        return {
            "provider": "gmail",
            "configured": True,
            "sent": False,
            "status": "connection_error",
            "error": str(exc),
        }


def send_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Send a rendered brief to a configured webhook."""

    webhook_url = os.environ.get("AGENTSCOUT_WEBHOOK_URL")
    if not webhook_url:
        return {
            "provider": "webhook",
            "configured": False,
            "sent": False,
            "status": "skipped_no_webhook",
            "detail": "Set AGENTSCOUT_WEBHOOK_URL to deliver scheduled briefs.",
        }

    body = json.dumps(
        {
            "subject": payload["subject"],
            "text": payload["text"],
            "html": payload["html"],
            "stories": payload["stories"],
            "next_actions": payload["next_actions"],
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("AGENTSCOUT_WEBHOOK_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        webhook_url,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_text = response.read().decode("utf-8", errors="replace")
            return {
                "provider": "webhook",
                "configured": True,
                "sent": 200 <= response.status < 300,
                "status": response.status,
                "response": response_text[:500],
            }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {
            "provider": "webhook",
            "configured": True,
            "sent": False,
            "status": exc.code,
            "error": detail[:500],
        }
    except urllib.error.URLError as exc:
        return {
            "provider": "webhook",
            "configured": True,
            "sent": False,
            "status": "connection_error",
            "error": str(exc),
        }
