"""
Email construction and delivery utilities.
"""

import math
import smtplib
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr
from typing import List

from .models import EmailContent, ScoredPaper

EMAIL_TEMPLATE = """
<!DOCTYPE HTML>
<html>
<head>
  <style>
    .star-wrapper {{
      font-size: 1.3em;
      line-height: 1;
      display: inline-flex;
      align-items: center;
    }}
    .half-star {{
      display: inline-block;
      width: 0.5em;
      overflow: hidden;
      white-space: nowrap;
      vertical-align: middle;
    }}
    .full-star {{
      vertical-align: middle;
    }}
  </style>
</head>
<body>

<div>
    {content}
</div>

<br><br>
<div>
To unsubscribe, remove your email in your Github Action setting.
</div>

</body>
</html>
"""


def get_stars_html(score: float) -> str:
    """
    Generate star rating HTML based on score.

    Args:
        score: Relevance score (0-10)

    Returns:
        HTML string with star rating
    """
    full_star = '<span class="full-star">⭐</span>'
    half_star = '<span class="half-star">⭐</span>'

    low = 6
    high = 8

    if score <= low:
        return ""
    elif score >= high:
        return full_star * 5
    else:
        interval = (high - low) / 10
        star_num = math.ceil((score - low) / interval)
        full_star_num = int(star_num / 2)
        half_star_num = star_num - full_star_num * 2
        return '<div class="star-wrapper">' + full_star * full_star_num + half_star * half_star_num + "</div>"


def create_paper_html(paper: ScoredPaper) -> str:
    """
    Create HTML block for a single paper.

    Args:
        paper: ScoredPaper to format

    Returns:
        HTML string for the paper
    """
    stars_html = get_stars_html(paper.score)

    # Format authors
    authors = paper.paper.authors[:5]
    authors_str = ", ".join(authors)
    if len(paper.paper.authors) > 5:
        authors_str += ", ..."

    # Format affiliations
    affiliations = []
    if paper.paper.affiliations:
        affiliations = paper.paper.affiliations[:5]
        affiliations_str = ", ".join(affiliations)
        if len(paper.paper.affiliations) > 5:
            affiliations_str += ", ..."
    else:
        affiliations_str = "Unknown Affiliation"

    # Code link
    code_link = ""
    if paper.paper.code_url:
        code_link = f'<a href="{paper.paper.code_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #5bc0de; padding: 8px 16px; border-radius: 4px; margin-left: 8px;">Code</a>'

    return f"""
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #333;">
            {paper.paper.title}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #666; padding: 8px 0;">
            {authors_str}
            <br>
            <i>{affiliations_str}</i>
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>Relevance:</strong> {stars_html}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>arXiv ID:</strong> {paper.paper.arxiv_id}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>TLDR:</strong> {paper.paper.tldr or 'No summary available'}
        </td>
    </tr>
    <tr>
        <td style="padding: 8px 0;">
            <a href="{paper.paper.pdf_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #d9534f; padding: 8px 16px; border-radius: 4px;">PDF</a>
            {code_link}
        </td>
    </tr>
    </table>
    """


def create_empty_email_html() -> str:
    """Create HTML for empty email (no papers found)."""
    return """
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #333;">
            No Papers Today. Take a Rest!
        </td>
    </tr>
    </table>
    """


def construct_email_content(papers: List[ScoredPaper]) -> EmailContent:
    """
    Construct complete email content from scored papers.

    Args:
        papers: List of scored papers to include

    Returns:
        EmailContent object or string content
    """

    if not papers:
        content = create_empty_email_html()
        return EmailContent(
            subject="Daily arXiv - No Papers Today", html_content=EMAIL_TEMPLATE.format(content=content), papers=[]
        )
    else:
        paper_blocks = [create_paper_html(paper) for paper in papers]
        content = "<br>".join(paper_blocks)

        return EmailContent(
            subject=f"Daily arXiv - {len(papers)} Papers",
            html_content=EMAIL_TEMPLATE.format(content=content),
            papers=papers,
        )


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
