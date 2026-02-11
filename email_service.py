import imaplib
import email

EMAIL = "civiceye463@gmail.com"
APP_PASSWORD = "bgos csgv uwqd bbhl"

def fetch_latest_email():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL, APP_PASSWORD)
    mail.select("inbox")

    status, messages = mail.search(None, "UNSEEN")
    email_ids = messages[0].split()

    if not email_ids:
        return None

    latest_id = email_ids[-1]
    status, msg_data = mail.fetch(latest_id, "(RFC822)")

    msg = email.message_from_bytes(msg_data[0][1])

    subject = msg["Subject"]
    sender = msg["From"]
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    return {
        "subject": subject,
        "body": body,
        "sender": sender
    }
