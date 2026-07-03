"""
Multi-channel alerts for illegal forest change verification.

SMS: Twilio when configured and SIMULATE_SMS is false.
Email: SendGrid HTTPS when SENDGRID_API_KEY is set; else Flask-Mail (SMTP) when SIMULATE_EMAIL is false.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from flask_mail import Mail, Message

from app.config import Config
from app.db_contacts import list_contacts_for_region

logger = logging.getLogger(__name__)

mail = Mail()


def init_mail(app) -> None:
    """Attach Flask-Mail to app from Config."""
    app.config.setdefault("MAIL_SERVER", Config.MAIL_SERVER)
    app.config.setdefault("MAIL_PORT", Config.MAIL_PORT)
    app.config.setdefault("MAIL_USE_TLS", Config.MAIL_USE_TLS)
    app.config.setdefault("MAIL_USE_SSL", Config.MAIL_USE_SSL)
    app.config.setdefault("MAIL_USERNAME", Config.MAIL_USERNAME)
    app.config.setdefault("MAIL_PASSWORD", Config.MAIL_PASSWORD)
    app.config.setdefault("MAIL_DEFAULT_SENDER", Config.MAIL_DEFAULT_SENDER)
    mail.init_app(app)


def _sms(body: str, to_phone: str) -> bool:
    """Send SMS via Twilio when enabled. Returns True only if Twilio accepted the message."""
    if not Config.TWILIO_ENABLED:
        logger.info("[SMS skipped: TWILIO_ENABLED=false] to=%s", to_phone)
        return False
    if Config.SIMULATE_SMS:
        logger.info(
            "[SMS SIMULATION only — set SIMULATE_SMS=false in .env to send via Twilio] to=%s | %s",
            to_phone,
            body[:500],
        )
        return False
    try:
        from twilio.base.exceptions import TwilioRestException
        from twilio.rest import Client

        has_ms = bool(Config.TWILIO_MESSAGING_SERVICE_SID)
        if not Config.TWILIO_ACCOUNT_SID or not Config.TWILIO_AUTH_TOKEN:
            logger.warning("Twilio SID/token missing; logging SMS instead")
            logger.info("[SMS FALLBACK LOG] to=%s | %s", to_phone, body[:500])
            return False
        if not has_ms and not Config.TWILIO_FROM_NUMBER:
            logger.warning("Set TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID")
            logger.info("[SMS FALLBACK LOG] to=%s | %s", to_phone, body[:500])
            return False
        client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        payload: dict[str, Any] = {
            "body": body[:1600],
            "to": to_phone,
        }
        if has_ms:
            payload["messaging_service_sid"] = Config.TWILIO_MESSAGING_SERVICE_SID
        else:
            payload["from_"] = Config.TWILIO_FROM_NUMBER
        msg = client.messages.create(**payload)
        logger.info(
            "SMS accepted by Twilio to=%s sid=%s status=%s (check Console if delivery fails)",
            to_phone,
            getattr(msg, "sid", ""),
            getattr(msg, "status", ""),
        )
        return True
    except TwilioRestException as exc:
        if getattr(exc, "code", None) == 21608:
            logger.warning(
                "SMS blocked for %s (Twilio trial: verify this number in Console > "
                "Phone Numbers > Verified Caller IDs, or upgrade the account). "
                "See https://www.twilio.com/docs/errors/21608",
                to_phone,
            )
        else:
            logger.error("SMS Twilio error for %s: %s", to_phone, exc)
        return False
    except Exception:
        logger.exception("SMS send failed for %s", to_phone)
        return False


def _email_via_sendgrid(subject: str, body: str, to_email: str) -> None:
    """POST /v3/mail/send — uses HTTPS :443 (often allowed when SMTP to Gmail is blocked)."""
    key = Config.SENDGRID_API_KEY
    sender = (Config.MAIL_DEFAULT_SENDER or Config.MAIL_USERNAME or "").strip()
    if "@" not in sender:
        logger.error(
            "SendGrid: set MAIL_DEFAULT_SENDER (or MAIL_USERNAME) to a verified sender email in SendGrid."
        )
        return
    payload: dict[str, Any] = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": sender},
        "subject": subject[:998],
        "content": [{"type": "text/plain", "value": body}],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            code = resp.getcode()
            if code in (200, 202):
                logger.info("Email sent via SendGrid (HTTPS) to %s", to_email)
            else:
                logger.warning("SendGrid unexpected status %s for %s", code, to_email)
    except urllib.error.HTTPError as exc:
        err_txt = exc.read().decode("utf-8", errors="replace")[:800]
        logger.error(
            "SendGrid HTTP %s for %s: %s — verify API key and Single Sender in SendGrid dashboard.",
            exc.code,
            to_email,
            err_txt,
        )
    except urllib.error.URLError as exc:
        logger.error("SendGrid network error for %s: %s", to_email, exc)
    except Exception:
        logger.exception("SendGrid send failed for %s", to_email)


def _email(subject: str, body: str, to_email: str, recipient_name: str) -> None:
    if Config.SIMULATE_EMAIL:
        logger.info(
            "[EMAIL SIMULATION] to=%s (%s) subject=%s | %s",
            to_email,
            recipient_name,
            subject,
            body[:800],
        )
        return
    to_email = to_email.strip()
    if "@" not in to_email:
        logger.warning(
            "Skipping email: invalid address %r (missing @). "
            "Fix telangana_alert_contacts.email in Postgres.",
            to_email,
        )
        return
    if Config.SENDGRID_API_KEY:
        _email_via_sendgrid(subject, body, to_email)
        return
    try:
        msg = Message(
            subject=subject,
            recipients=[to_email],
            body=body,
        )
        mail.send(msg)
        logger.info("Email sent via SMTP to %s", to_email)
    except TimeoutError:
        logger.error(
            "Email send failed for %s: SMTP timed out to %s:%s. "
            "This network often blocks SMTP. Options: (1) phone hotspot / home WiFi, "
            "(2) set SENDGRID_API_KEY in .env — email then uses HTTPS.",
            to_email,
            Config.MAIL_SERVER,
            Config.MAIL_PORT,
        )
    except OSError as exc:
        if exc.errno == 10060 or "timed out" in str(exc).lower():
            logger.error(
                "Email send failed for %s: cannot reach %s:%s (%s). "
                "Try SENDGRID_API_KEY (HTTPS) or a different network.",
                to_email,
                Config.MAIL_SERVER,
                Config.MAIL_PORT,
                exc,
            )
        else:
            logger.exception("Email send failed for %s", to_email)
    except Exception:
        logger.exception("Email send failed for %s", to_email)


def send_illegal_alerts(analysis: dict[str, Any]) -> dict[str, Any]:
    """
    Notify all contact roles for the region. Only call for illegal verification.
    Returns counts and channels used.
    """
    region_slug = analysis.get("region_slug") or ""
    contacts = list_contacts_for_region(region_slug)
    operator_to = Config.operator_illegal_alert_email()
    if Config.ALERT_EMAIL_CONTACTS_ONLY_OPERATOR and not operator_to:
        logger.warning(
            "ALERT_EMAIL_CONTACTS_ONLY_OPERATOR=true but operator_illegal_alert_email() is empty; "
            "set MAIL_USERNAME or ALERT_NOTIFY_EMAIL to a real address."
        )
    summary: dict[str, Any] = {
        "region_slug": region_slug,
        "sms": 0,
        "sms_delivered": 0,
        "sms_failed": 0,
        "email": 0,
        "contacts_notified": len(contacts),
        "email_operator_copy": False,
    }

    subject = f"[Eco-Guard Telangana] Illegal forest change alert — {region_slug}"
    body = (
        f"Illegal forest change verified.\n"
        f"Region: {analysis.get('region_name', region_slug)}\n"
        f"Loss %: {analysis.get('loss_percent')}\n"
        f"Status: {analysis.get('status')}\n"
        f"Analysis ID: {analysis.get('analysis_id')}\n"
        f"Simulated GEE: {analysis.get('simulated')}\n"
    )
    sms_text = f"{subject}\n{body}"
    if Config.TWILIO_SMS_SHORT_BODY:
        aid = str(analysis.get("analysis_id") or "")[:12]
        sms_text = (
            f"Eco-Guard ILLEGAL alert: {analysis.get('region_name', region_slug)} "
            f"loss {analysis.get('loss_percent')}% ref {aid}"
        )[:480]

    phones_sent: set[str] = set()

    if not Config.TWILIO_SMS_ALL_CONTACTS and Config.TWILIO_ENABLED and not Config.SIMULATE_SMS:
        logger.info(
            "TWILIO_SMS_ALL_CONTACTS=false: skipping SMS to Postgres demo contacts; "
            "only ALERT_TO_NUMBER will be texted (%s)",
            (Config.ALERT_TO_NUMBER or "(not set)").strip() or "(not set)",
        )

    emailed_lower: set[str] = set()

    for c in contacts:
        name = c.get("name", "")
        phone = (c.get("phone") or "").strip()
        email_addr = (c.get("email") or "").strip()

        if phone:
            phones_sent.add(phone)
            if not Config.TWILIO_SMS_ALL_CONTACTS:
                continue
            ok = _sms(sms_text, phone)
            if ok:
                summary["sms_delivered"] += 1
            elif Config.TWILIO_ENABLED and not Config.SIMULATE_SMS:
                summary["sms_failed"] += 1
        if email_addr and not Config.ALERT_EMAIL_CONTACTS_ONLY_OPERATOR:
            _email(subject, f"Dear {name},\n\n{body}", email_addr, name)
            summary["email"] += 1
            emailed_lower.add(email_addr.strip().lower())

    if operator_to:
        op_lower = operator_to.lower()
        if op_lower not in emailed_lower:
            copy_body = (
                "You are receiving this operator copy because MAIL_USERNAME or ALERT_NOTIFY_EMAIL "
                "is set in .env (and SIMULATE_EMAIL is false).\n\n"
                + body
            )
            _email(subject, copy_body, operator_to, "Operator")
            summary["email"] += 1
            summary["email_operator_copy"] = True

    extra = (Config.ALERT_TO_NUMBER or "").strip()
    if extra:
        send_extra = (not Config.TWILIO_SMS_ALL_CONTACTS) or (extra not in phones_sent)
        if send_extra:
            ok = _sms(sms_text, extra)
            if ok:
                summary["sms_delivered"] += 1
            elif Config.TWILIO_ENABLED and not Config.SIMULATE_SMS:
                summary["sms_failed"] += 1

    summary["sms"] = summary["sms_delivered"]

    summary["sms_delivery"] = (
        "disabled_twilio"
        if not Config.TWILIO_ENABLED
        else ("simulated_log_only" if Config.SIMULATE_SMS else "twilio_live")
    )

    logger.info("Alert dispatch complete: %s", summary)
    return summary