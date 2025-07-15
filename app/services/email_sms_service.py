import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging

logger = logging.getLogger(__name__)

class EmailSMSService:
    def __init__(self, app_config):
        self.app_config = app_config
        self.twilio_client = self._init_twilio_client()

    def _init_twilio_client(self):
        try:
            account_sid = self.app_config.TWILIO_ACCOUNT_SID
            auth_token = self.app_config.TWILIO_AUTH_TOKEN
            if account_sid and auth_token:
                return Client(account_sid, auth_token)
            else:
                logger.warning("Twilio credentials not found or incomplete. SMS service will be unavailable.")
                return None
        except Exception as e:
            logger.error(f"Error initializing Twilio client: {e}", exc_info=True)
            return None

    def send_email(self, recipient_email, subject, body):
        if not self.app_config.EMAIL_HOST_USER or not self.app_config.EMAIL_HOST_PASSWORD:
            logger.error("Email sender credentials are not set. Cannot send email.")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.app_config.EMAIL_HOST_USER
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html')) # atau 'plain'

            with smtplib.SMTP(self.app_config.EMAIL_HOST, self.app_config.EMAIL_PORT) as server:
                server.starttls()
                server.login(self.app_config.EMAIL_HOST_USER, self.app_config.EMAIL_HOST_PASSWORD)
                server.send_message(msg)
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}", exc_info=True)
            return False

    def send_sms(self, to_phone_number, message):
        if not self.twilio_client:
            logger.error("Twilio client not initialized. Cannot send SMS.")
            return False
        if not self.app_config.TWILIO_PHONE_NUMBER:
            logger.error("Twilio sender phone number not set. Cannot send SMS.")
            return False

        try:
            message = self.twilio_client.messages.create(
                to=to_phone_number,
                from_=self.app_config.TWILIO_PHONE_NUMBER,
                body=message
            )
            logger.info(f"SMS sent successfully to {to_phone_number}, SID: {message.sid}")
            return True
        except TwilioRestException as e:
            logger.error(f"Twilio SMS error to {to_phone_number}: {e.msg} (Code: {e.code})", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone_number}: {e}", exc_info=True)
            return False