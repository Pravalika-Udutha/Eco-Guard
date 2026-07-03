"""Multi-channel alert system for forest change notifications."""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.forest import AlertRecipient, ForestChange, ForestChangeVerification
from app.core.config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """Send alerts via SMS and email."""

    @staticmethod
    def send_sms_alert(phone: str, message: str) -> bool:
        """Send SMS alert via Twilio."""
        try:
            from twilio.rest import Client

            if not settings.twilio_enabled:
                logger.info(f"SMS (SIMULATION): {phone} - {message[:100]}")
                return True

            if not all([
                settings.twilio_account_sid,
                settings.twilio_auth_token,
                settings.twilio_from_number,
            ]):
                logger.warning("Twilio not configured")
                return False

            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            msg = client.messages.create(
                body=message[:1600],
                from_=settings.twilio_from_number,
                to=phone,
            )
            logger.info(f"SMS sent to {phone} (SID: {msg.sid})")
            return True
        except Exception as e:
            logger.error(f"SMS send failed to {phone}: {e}")
            return False

    @staticmethod
    def send_email_alert(email: str, recipient_name: str, subject: str, message: str) -> bool:
        """Send email alert."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # For now, log as simulation
            logger.info(f"EMAIL (SIMULATION): {email}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   To: {recipient_name}")
            logger.info(f"   Preview: {message[:100]}...")

            # TODO: Configure SMTP in .env for production
            return True
        except Exception as e:
            logger.error(f"Email send failed to {email}: {e}")
            return False


def build_alert_message(
    change: ForestChange,
    verification: ForestChangeVerification,
    db: Session,
) -> str:
    """Build alert message with forest change details."""
    ndvi_loss = change.ndvi_before - change.ndvi_after
    area_hectares = (change.area_affected_sq_meters / 10000) if change.area_affected_sq_meters else 0

    message = f"""
ILLEGAL FOREST CHANGE DETECTED

Region: Forest Area ID {change.region_id}
Location: {change.latitude}N, {change.longitude}E
Date Detected: {change.change_date}
Detection Confidence: {change.detection_confidence * 100:.1f}%

Change Type: {verification.change_type or 'Unknown'}
Vegetation Loss (NDVI): {ndvi_loss:.3f}
Area Affected: {area_hectares:.2f} hectares
Satellite: {change.satellite_source}

Admin Notes: {verification.verification_notes or 'No additional notes'}

Status: VERIFIED ILLEGAL
Action Required: Immediate investigation and intervention

---
Eco-Guard Forest Monitoring System
For urgent response, contact your regional forest officer.
"""
    return message


def send_illegal_change_alerts(
    db: Session,
    change: ForestChange,
    verification: ForestChangeVerification,
    recipient_list: list[AlertRecipient],
) -> dict:
    """
    Send multi-channel alerts for an illegal forest change.

    Returns:
        Dictionary with alert statistics
    """
    alert_service = AlertService()
    alert_channels = verification.alert_channels.split(",") if verification.alert_channels else []
    alert_channels = [ch.strip().upper() for ch in alert_channels]

    stats = {
        "total_recipients": len(recipient_list),
        "sms_sent": 0,
        "email_sent": 0,
        "failed": 0,
        "sent_to": [],
    }

    message = build_alert_message(change, verification, db)

    for recipient in recipient_list:
        recipient_info = f"{recipient.name} ({recipient.organization})"

        if "SMS" in alert_channels and recipient.phone:
            sms_msg = f"ILLEGAL Forest Change at {change.latitude:.4f},{change.longitude:.4f}. NDVI Loss: {change.ndvi_before - change.ndvi_after:.3f}. Area: {(change.area_affected_sq_meters or 0)/10000:.1f}ha. Check email for details."
            if alert_service.send_sms_alert(recipient.phone, sms_msg):
                stats["sms_sent"] += 1
                logger.info(f"SMS sent to {recipient_info}")
            else:
                stats["failed"] += 1

        if "EMAIL" in alert_channels and recipient.email:
            subject = "ILLEGAL Forest Change Detected - Immediate Action Required"
            if alert_service.send_email_alert(
                recipient.email,
                recipient.name,
                subject,
                message
            ):
                stats["email_sent"] += 1
                logger.info(f"Email sent to {recipient_info}")
            else:
                stats["failed"] += 1

        stats["sent_to"].append(recipient_info)

    verification.alert_sent = True
    verification.alert_sent_at = datetime.now()
    db.commit()
    db.refresh(verification)

    logger.info(
        f"Alert campaign complete. Recipients: {stats['total_recipients']}, "
        f"SMS: {stats['sms_sent']}, Email: {stats['email_sent']}, Failed: {stats['failed']}"
    )

    return stats