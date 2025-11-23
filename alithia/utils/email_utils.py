"""
Email construction and delivery utilities.
"""

import smtplib
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr


def send_email(sender: str, receiver: str, password: str, smtp_server: str, smtp_port: int, html_content: str) -> bool:
    """
    Send email via SMTP.

    Args:
        sender: Sender email address
        receiver: Receiver email address
        password: Sender email password
        smtp_server: SMTP server address
        smtp_port: SMTP server port
        html_content: HTML content to send

    Returns:
        True if email sent successfully, False otherwise
    """
    if sender == "" or receiver == "" or password == "" or smtp_server == "" or smtp_port == 0:
        raise Exception("Email configuration is not set correctly")

    def _format_addr(s):
        name, addr = parseaddr(s)
        return formataddr((Header(name, "utf-8").encode(), addr))

    msg = MIMEText(html_content, "html", "utf-8")
    msg["From"] = _format_addr(f"Github Action <{sender}>")
    msg["To"] = _format_addr(f"You <{receiver}>")

    today = datetime.now().strftime("%Y/%m/%d")
    msg["Subject"] = Header(f"Daily arXiv {today}", "utf-8").encode()

    server = None
    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        server.ehlo()
        server.starttls()
        server.ehlo()
    except Exception as e:
        if server:
            try:
                server.quit()
            except:
                pass
        try:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
            server.ehlo()
        except Exception as ssl_error:
            raise Exception(f"Failed to connect to SMTP server: {e} (TLS) and {ssl_error} (SSL)")

    try:
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        return True
    except Exception as e:
        raise Exception(f"Unexpected error during email sending: {e}")
    finally:
        if server:
            try:
                server.quit()
            except:
                pass
