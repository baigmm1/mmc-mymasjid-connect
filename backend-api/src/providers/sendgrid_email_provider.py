"""
SendGrid email provider integration.

Provides functionality to send transactional and marketing emails using SendGrid API.
"""

from typing import Optional, List, Dict, Any
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail,
    Email,
    To,
    Content,
    Attachment,
    FileContent,
    FileName,
    FileType,
    Disposition,
    Personalization,
)
from python_http_client.exceptions import HTTPError

from src.core.logging import get_logger
from src.config import settings

logger = get_logger(__name__, level=settings.LOG_LEVEL)


class SendGridEmailProvider:
    """SendGrid email provider for sending transactional and marketing emails."""

    def __init__(self, api_key: str, from_email: str, from_name: Optional[str] = None):
        """
        Initialize SendGrid client with the provided API key.

        Args:
            api_key: SendGrid API key
            from_email: Default sender email address
            from_name: Default sender name (optional)
        """
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name or "Masjid Connect"
        self.client = SendGridAPIClient(api_key=self.api_key)
        
        logger.debug(f"SendGridAPIClient initialized with API key: {self.api_key[:4]}****")
        logger.debug(f"SendGridEmailProvider initialized with from_email: {self.from_email}")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: Optional[str] = None,
        plain_text_content: Optional[str] = None,
        to_name: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to_email: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        custom_args: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send an email using SendGrid.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML content of the email (optional)
            plain_text_content: Plain text content of the email (optional)
            to_name: Recipient name (optional)
            from_email: Sender email address (overrides default)
            from_name: Sender name (overrides default)
            reply_to_email: Reply-to email address (optional)
            cc_emails: List of CC email addresses (optional)
            bcc_emails: List of BCC email addresses (optional)
            attachments: List of attachment dictionaries with 'content', 'filename', 'type' keys
            custom_args: Custom arguments for tracking (optional)

        Returns:
            Dictionary with status code and response body

        Raises:
            HTTPError: If SendGrid API request fails
            Exception: For unexpected errors
        """
        try:
            # Use provided from_email or default
            sender_email = from_email or self.from_email
            sender_name = from_name or self.from_name

            # Create email message
            message = Mail(
                from_email=Email(sender_email, sender_name),
                to_emails=To(to_email, to_name),
                subject=subject,
            )

            # Add content (at least one is required)
            if html_content:
                message.content = Content("text/html", html_content)
            elif plain_text_content:
                message.content = Content("text/plain", plain_text_content)
            else:
                raise ValueError("Either html_content or plain_text_content must be provided")

            # Add plain text as alternative if both provided
            if html_content and plain_text_content:
                message.add_content(Content("text/plain", plain_text_content))

            # Add reply-to if provided
            if reply_to_email:
                message.reply_to = Email(reply_to_email)

            # Add CC recipients
            if cc_emails:
                personalization = Personalization()
                personalization.add_to(To(to_email, to_name))
                for cc_email in cc_emails:
                    personalization.add_cc(Email(cc_email))
                message.personalization = [personalization]

            # Add BCC recipients
            if bcc_emails:
                if not hasattr(message, 'personalization') or not message.personalization:
                    personalization = Personalization()
                    personalization.add_to(To(to_email, to_name))
                    message.personalization = [personalization]
                
                for bcc_email in bcc_emails:
                    message.personalization[0].add_bcc(Email(bcc_email))

            # Add attachments
            if attachments:
                for attachment_data in attachments:
                    attachment = Attachment(
                        file_content=FileContent(attachment_data.get('content', '')),
                        file_name=FileName(attachment_data.get('filename', 'attachment')),
                        file_type=FileType(attachment_data.get('type', 'application/octet-stream')),
                        disposition=Disposition('attachment')
                    )
                    message.add_attachment(attachment)

            # Add custom arguments for tracking
            if custom_args:
                message.custom_arg = custom_args

            # Send email
            response = self.client.send(message)
            
            logger.info(
                f"Email sent successfully to {to_email}",
                extra={
                    "to_email": to_email,
                    "subject": subject,
                    "status_code": response.status_code,
                }
            )

            return {
                "status_code": response.status_code,
                "body": response.body,
                "headers": dict(response.headers),
                "success": True,
            }

        except HTTPError as e:
            logger.error(
                f"SendGrid HTTP error occurred: {e.reason}",
                extra={
                    "to_email": to_email,
                    "status_code": e.status_code,
                    "error_body": e.body,
                },
                exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error occurred while sending email: {str(e)}",
                extra={"to_email": to_email, "error": str(e)},
                exc_info=True
            )
            raise

    async def send_template_email(
        self,
        to_email: str,
        template_id: str,
        dynamic_template_data: Dict[str, Any],
        to_name: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to_email: Optional[str] = None,
        custom_args: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send an email using a SendGrid dynamic template.

        Args:
            to_email: Recipient email address
            template_id: SendGrid template ID
            dynamic_template_data: Dictionary of template variables
            to_name: Recipient name (optional)
            from_email: Sender email address (overrides default)
            from_name: Sender name (overrides default)
            reply_to_email: Reply-to email address (optional)
            custom_args: Custom arguments for tracking (optional)

        Returns:
            Dictionary with status code and response body

        Raises:
            HTTPError: If SendGrid API request fails
            Exception: For unexpected errors
        """
        try:
            # Use provided from_email or default
            sender_email = from_email or self.from_email
            sender_name = from_name or self.from_name

            # Create email message with template
            message = Mail(
                from_email=Email(sender_email, sender_name),
                to_emails=To(to_email, to_name),
            )

            # Set template ID and dynamic data
            message.template_id = template_id
            message.dynamic_template_data = dynamic_template_data

            # Add reply-to if provided
            if reply_to_email:
                message.reply_to = Email(reply_to_email)

            # Add custom arguments for tracking
            if custom_args:
                message.custom_arg = custom_args

            # Send email
            response = self.client.send(message)
            
            logger.info(
                f"Template email sent successfully to {to_email}",
                extra={
                    "to_email": to_email,
                    "template_id": template_id,
                    "status_code": response.status_code,
                }
            )

            return {
                "status_code": response.status_code,
                "body": response.body,
                "headers": dict(response.headers),
                "success": True,
            }

        except HTTPError as e:
            logger.error(
                f"SendGrid HTTP error occurred: {e.reason}",
                extra={
                    "to_email": to_email,
                    "template_id": template_id,
                    "status_code": e.status_code,
                    "error_body": e.body,
                },
                exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error occurred while sending template email: {str(e)}",
                extra={"to_email": to_email, "template_id": template_id, "error": str(e)},
                exc_info=True
            )
            raise

    async def send_bulk_emails(
        self,
        recipients: List[Dict[str, str]],
        subject: str,
        html_content: Optional[str] = None,
        plain_text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send bulk emails to multiple recipients.

        Args:
            recipients: List of recipient dictionaries with 'email' and optional 'name' keys
            subject: Email subject line
            html_content: HTML content of the email (optional)
            plain_text_content: Plain text content of the email (optional)
            from_email: Sender email address (overrides default)
            from_name: Sender name (overrides default)

        Returns:
            Dictionary with status code and response body

        Raises:
            HTTPError: If SendGrid API request fails
            Exception: For unexpected errors
        """
        try:
            # Use provided from_email or default
            sender_email = from_email or self.from_email
            sender_name = from_name or self.from_name

            # Create personalization for each recipient
            personalizations = []
            for recipient in recipients:
                personalization = Personalization()
                personalization.add_to(
                    To(recipient['email'], recipient.get('name'))
                )
                personalizations.append(personalization)

            # Create email message
            message = Mail(
                from_email=Email(sender_email, sender_name),
                subject=subject,
            )

            # Add content
            if html_content:
                message.content = Content("text/html", html_content)
            elif plain_text_content:
                message.content = Content("text/plain", plain_text_content)
            else:
                raise ValueError("Either html_content or plain_text_content must be provided")

            # Add personalizations
            message.personalization = personalizations

            # Send email
            response = self.client.send(message)
            
            logger.info(
                f"Bulk email sent successfully to {len(recipients)} recipients",
                extra={
                    "recipient_count": len(recipients),
                    "subject": subject,
                    "status_code": response.status_code,
                }
            )

            return {
                "status_code": response.status_code,
                "body": response.body,
                "headers": dict(response.headers),
                "success": True,
                "recipient_count": len(recipients),
            }

        except HTTPError as e:
            logger.error(
                f"SendGrid HTTP error occurred during bulk send: {e.reason}",
                extra={
                    "recipient_count": len(recipients),
                    "status_code": e.status_code,
                    "error_body": e.body,
                },
                exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error occurred while sending bulk emails: {str(e)}",
                extra={"recipient_count": len(recipients), "error": str(e)},
                exc_info=True
            )
            raise


# async def get_sendgrid_provider(
#     api_key: Optional[str] = None,
#     from_email: Optional[str] = None,
#     from_name: Optional[str] = None,
# ) -> SendGridEmailProvider:
#     """
#     Get SendGrid email provider instance.

#     Args:
#         api_key: SendGrid API key (uses settings.SENDGRID_API_KEY if not provided)
#         from_email: Sender email address (uses settings.SENDGRID_FROM_EMAIL if not provided)
#         from_name: Sender name (uses settings.SENDGRID_FROM_NAME if not provided)

#     Returns:
#         SendGridEmailProvider instance

#     Raises:
#         ValueError: If API key or from_email is not provided and not in settings
#     """
#     api_key = api_key or settings.SENDGRID_API_KEY
#     from_email = from_email or settings.SENDGRID_FROM_EMAIL
#     from_name = from_name or settings.SENDGRID_FROM_NAME

#     if not api_key:
#         raise ValueError("SendGrid API key is required. Set SENDGRID_API_KEY environment variable.")
    
#     if not from_email:
#         raise ValueError("SendGrid from_email is required. Set SENDGRID_FROM_EMAIL environment variable.")

#     return SendGridEmailProvider(api_key=api_key, from_email=from_email, from_name=from_name)
