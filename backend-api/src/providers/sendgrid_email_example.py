"""
Example usage of SendGrid Email Provider.

This file demonstrates how to use the SendGrid email provider in your endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

from src.providers.sendgrid_email_provider import get_sendgrid_provider
from src.core.logging import get_logger
from src.config import settings

router = APIRouter(prefix="/email", tags=["email"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


class EmailRequest(BaseModel):
    """Request model for sending email."""
    to_email: EmailStr
    to_name: Optional[str] = None
    subject: str
    html_content: Optional[str] = None
    plain_text_content: Optional[str] = None


class TemplateEmailRequest(BaseModel):
    """Request model for sending template email."""
    to_email: EmailStr
    to_name: Optional[str] = None
    template_id: str
    template_data: dict


@router.post("/send")
async def send_email(request: EmailRequest):
    """
    Send a simple email.
    
    Example usage:
    ```python
    POST /api/v1/email/send
    {
        "to_email": "recipient@example.com",
        "to_name": "John Doe",
        "subject": "Welcome to Masjid Connect",
        "html_content": "<h1>Welcome!</h1><p>Thank you for joining us.</p>",
        "plain_text_content": "Welcome! Thank you for joining us."
    }
    ```
    """
    try:
        provider = await get_sendgrid_provider()
        
        result = await provider.send_email(
            to_email=request.to_email,
            to_name=request.to_name,
            subject=request.subject,
            html_content=request.html_content,
            plain_text_content=request.plain_text_content,
        )
        
        return {
            "success": True,
            "message": f"Email sent successfully to {request.to_email}",
            "status_code": result["status_code"],
        }
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.post("/send-template")
async def send_template_email(request: TemplateEmailRequest):
    """
    Send an email using a SendGrid dynamic template.
    
    Example usage:
    ```python
    POST /api/v1/email/send-template
    {
        "to_email": "recipient@example.com",
        "to_name": "John Doe",
        "template_id": "d-1234567890abcdef",
        "template_data": {
            "first_name": "John",
            "donation_amount": "$100.00",
            "donation_date": "2025-12-31"
        }
    }
    ```
    """
    try:
        provider = await get_sendgrid_provider()
        
        result = await provider.send_template_email(
            to_email=request.to_email,
            to_name=request.to_name,
            template_id=request.template_id,
            dynamic_template_data=request.template_data,
        )
        
        return {
            "success": True,
            "message": f"Template email sent successfully to {request.to_email}",
            "status_code": result["status_code"],
        }
    except Exception as e:
        logger.error(f"Failed to send template email: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send template email: {str(e)}")


# Example: Sending donation receipt email
async def send_donation_receipt(
    donor_email: str,
    donor_name: str,
    donation_amount: float,
    donation_date: str,
    transaction_id: str,
):
    """
    Example function to send a donation receipt email.
    
    This would typically be called after a successful donation transaction.
    """
    try:
        provider = await get_sendgrid_provider()
        
        html_content = f"""
        <html>
            <body>
                <h1>Thank you for your donation!</h1>
                <p>Dear {donor_name},</p>
                <p>We have received your generous donation of ${donation_amount:.2f}.</p>
                <p><strong>Transaction Details:</strong></p>
                <ul>
                    <li>Amount: ${donation_amount:.2f}</li>
                    <li>Date: {donation_date}</li>
                    <li>Transaction ID: {transaction_id}</li>
                </ul>
                <p>Your donation is tax-deductible. Please keep this email for your records.</p>
                <p>Best regards,<br>Masjid Connect Team</p>
            </body>
        </html>
        """
        
        plain_text = f"""
        Thank you for your donation!
        
        Dear {donor_name},
        
        We have received your generous donation of ${donation_amount:.2f}.
        
        Transaction Details:
        - Amount: ${donation_amount:.2f}
        - Date: {donation_date}
        - Transaction ID: {transaction_id}
        
        Your donation is tax-deductible. Please keep this email for your records.
        
        Best regards,
        Masjid Connect Team
        """
        
        result = await provider.send_email(
            to_email=donor_email,
            to_name=donor_name,
            subject="Donation Receipt - Masjid Connect",
            html_content=html_content,
            plain_text_content=plain_text,
            custom_args={
                "transaction_id": transaction_id,
                "type": "donation_receipt",
            }
        )
        
        logger.info(
            f"Donation receipt sent to {donor_email}",
            extra={
                "donor_email": donor_email,
                "transaction_id": transaction_id,
                "donation_amount": donation_amount,
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(
            f"Failed to send donation receipt: {str(e)}",
            extra={
                "donor_email": donor_email,
                "transaction_id": transaction_id,
            },
            exc_info=True
        )
        raise


# Example: Sending bulk announcement emails
async def send_bulk_announcement(
    recipients: list[dict],
    subject: str,
    message: str,
):
    """
    Example function to send bulk announcement emails.
    
    Args:
        recipients: List of dicts with 'email' and 'name' keys
        subject: Email subject
        message: Email message content
    """
    try:
        provider = await get_sendgrid_provider()
        
        html_content = f"""
        <html>
            <body>
                <h1>Announcement from Masjid Connect</h1>
                <div>{message}</div>
                <hr>
                <p><small>You are receiving this email because you are subscribed to Masjid Connect announcements.</small></p>
            </body>
        </html>
        """
        
        result = await provider.send_bulk_emails(
            recipients=recipients,
            subject=subject,
            html_content=html_content,
            plain_text_content=message,
        )
        
        logger.info(
            f"Bulk announcement sent to {result['recipient_count']} recipients",
            extra={"recipient_count": result['recipient_count'], "subject": subject}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to send bulk announcement: {str(e)}", exc_info=True)
        raise
