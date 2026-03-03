"""
meetingmind/email.py — Email notifications
Triggers:
  1. Member assigned a new task
  2. Task marked overdue (HIGH still open after 3 days)
  3. Member completes all their tasks
"""
import os
import ssl
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
APP_URL = os.getenv("APP_URL", "http://localhost:8091")

def _html_wrapper(title: str, body: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Georgia', serif; background: #f5f5f0; margin: 0; padding: 40px 20px; }}
  .container {{ max-width: 560px; margin: 0 auto; background: #fff;
                border: 1px solid #ddddd8; border-radius: 8px; overflow: hidden; }}
  .header {{ background: #0a0a0a; padding: 24px 32px; display: flex; align-items: center; gap: 10px; }}
  .header-logo {{ font-family: sans-serif; font-size: 1.1rem; font-weight: 800;
                  letter-spacing: -0.5px; color: #fff; }}
  .header-dot {{ width: 8px; height: 8px; border-radius: 50%; background: #e8ff47;
                 display: inline-block; margin-right: 8px; }}
  .body {{ padding: 32px; }}
  h2 {{ font-size: 1.3rem; font-weight: normal; letter-spacing: -0.5px;
        color: #0a0a0a; margin-bottom: 12px; }}
  p {{ font-size: 0.88rem; color: #555; line-height: 1.7; margin-bottom: 16px; }}
  .item-card {{ background: #f9f9f4; border: 1px solid #ddddd8; border-radius: 6px;
                padding: 14px 16px; margin-bottom: 12px; border-left: 3px solid #0a0a0a; }}
  .item-card.high {{ border-left-color: #c0392b; }}
  .item-card.medium {{ border-left-color: #0066cc; }}
  .item-card.low {{ border-left-color: #888; }}
  .item-priority {{ font-size: 0.65rem; font-weight: bold; letter-spacing: 1px;
                    text-transform: uppercase; margin-bottom: 6px; }}
  .item-priority.high {{ color: #c0392b; }}
  .item-priority.medium {{ color: #0066cc; }}
  .item-priority.low {{ color: #888; }}
  .item-text {{ font-size: 0.85rem; color: #0a0a0a; line-height: 1.4; }}
  .item-meta {{ font-size: 0.72rem; color: #aaa; margin-top: 4px; }}
  .btn {{ display: inline-block; padding: 12px 24px; background: #0a0a0a; color: #fff;
          text-decoration: none; border-radius: 5px; font-size: 0.82rem;
          font-family: monospace; letter-spacing: 0.5px; margin-top: 8px; }}
  .footer {{ padding: 20px 32px; border-top: 1px solid #ddddd8;
             font-size: 0.72rem; color: #aaa; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <span class="header-dot"></span>
    <span class="header-logo">MeetingMind</span>
  </div>
  <div class="body">
    <h2>{title}</h2>
    {body}
  </div>
  <div class="footer">
    You're receiving this because you're a member of a MeetingMind team.<br>
    <a href="{APP_URL}" style="color:#aaa">Open MeetingMind</a>
  </div>
</div>
</body>
</html>
"""

async def send_email(to: str, subject: str, html: str):
    """Send an email via Gmail SMTP."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print(f"[EMAIL] Skipped (no credentials): {subject} → {to}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"MeetingMind <{GMAIL_USER}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=465,
            username=GMAIL_USER,
            password=GMAIL_APP_PASSWORD,
            use_tls=True,
        )
        print(f"[EMAIL] Sent: {subject} → {to}")
    except Exception as e:
        print(f"[EMAIL] Failed: {e}")


async def notify_task_assigned(member_email: str, member_name: str,
                                item_text: str, priority: str,
                                meeting_title: str, manager_name: str):
    """Email sent when a manager assigns a task to a member."""
    subject = f"New task assigned — {priority.upper()} priority"
    body = f"""
    <p>Hi {member_name},</p>
    <p><strong>{manager_name}</strong> has assigned you a new action item from
       <strong>{meeting_title}</strong>:</p>
    <div class="item-card {priority}">
      <div class="item-priority {priority}">{priority.upper()}</div>
      <div class="item-text">{item_text}</div>
      <div class="item-meta">from: {meeting_title}</div>
    </div>
    <p>Log in to update your progress.</p>
    <a href="{APP_URL}/tasks" class="btn">View My Tasks →</a>
    """
    await send_email(member_email, subject, _html_wrapper(
        f"You have a new {priority.upper()} task", body
    ))


async def notify_all_tasks_complete(member_email: str, member_name: str,
                                     manager_email: str, manager_name: str,
                                     total: int):
    """Email sent to both member and manager when member completes all tasks."""
    subject = f"{member_name} completed all their tasks!"

    member_body = f"""
    <p>Hi {member_name},</p>
    <p>You've completed all <strong>{total}</strong> of your assigned tasks.
       Great work! Check back after the next meeting for new assignments.</p>
    <a href="{APP_URL}/tasks" class="btn">View My Tasks →</a>
    """
    await send_email(member_email, "All tasks complete!", _html_wrapper(
        "All done!", member_body
    ))

    manager_body = f"""
    <p>Hi {manager_name},</p>
    <p><strong>{member_name}</strong> has completed all <strong>{total}</strong>
       of their assigned tasks.</p>
    <a href="{APP_URL}/dashboard" class="btn">View Workload →</a>
    """
    await send_email(manager_email, subject, _html_wrapper(
        f"{member_name} is all clear", manager_body
    ))


async def notify_overdue_items(manager_email: str, manager_name: str,
                                overdue_items: list):
    """
    Email sent to manager when HIGH items are still open after 3 days.
    overdue_items: list of dicts with keys: owner_name, text, meeting_title, days_open
    """
    if not overdue_items:
        return

    subject = f"Overdue alert — {len(overdue_items)} HIGH items unresolved"

    items_html = "".join([f"""
    <div class="item-card high">
      <div class="item-priority high">HIGH — {item['days_open']} days open</div>
      <div class="item-text">{item['text']}</div>
      <div class="item-meta">Owner: {item['owner_name']} · from: {item['meeting_title']}</div>
    </div>
    """ for item in overdue_items])

    body = f"""
    <p>Hi {manager_name},</p>
    <p>The following <strong>HIGH priority items</strong> have been open for
       more than 3 days and need attention:</p>
    {items_html}
    <a href="{APP_URL}/dashboard" class="btn">View Dashboard →</a>
    """
    await send_email(manager_email, subject, _html_wrapper(
        f"{len(overdue_items)} overdue HIGH items", body
    ))