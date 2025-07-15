import qrcode
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

class QRCodeService:
    def generate_qr_code(self, data, box_size=10, border=4):
        """
        Generates a QR code image as bytes.
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=box_size,
                border=border,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            logger.info(f"QR code generated for data: {data[:20]}...")
            return buf.getvalue()
        except Exception as e:
            logger.error(f"Error generating QR code for data {data[:20]}...: {e}", exc_info=True)
            return None

    def save_qr_code_to_file(self, data, filename):
        """
        Generates and saves a QR code image to a file. (Mostly for debugging/local use)
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(filename)
            logger.info(f"QR code saved to file: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving QR code to file {filename}: {e}", exc_info=True)
            return None