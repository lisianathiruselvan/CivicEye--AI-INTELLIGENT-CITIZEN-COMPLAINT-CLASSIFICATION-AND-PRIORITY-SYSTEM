import streamlit as st
import pandas as pd
import html
import imaplib
import email
from predict_service import predict_complaint
import os
import matplotlib.pyplot as plt
plt.rcParams["figure.autolayout"] = True

import base64
# ---- PAGE CONFIG ----
st.set_page_config(page_title="CivicEye", page_icon="🚨", layout="wide")


def set_bg(image_file):
    import base64
    import streamlit as st

    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    st.markdown(f"""
    <style>
    /* ---------- APP BACKGROUND ---------- */
    .stApp {{
        background-image: url("data:image/jpeg;base64,{encoded}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}

    /* ---------- CARDS, TABLES, ALERTS ---------- */
    div[class*="stCard"],
    [data-testid="stDataFrame"],
    div.stAlert {{
        background-color: #f0f2f6 !important;
        opacity: 1 !important;
        border-radius: 12px;
        padding: 15px;
    }}

    div[data-testid="stDataFrame"] div[role="grid"] {{
        background-color: #f0f2f6 !important;
        opacity: 1 !important;
    }}

    div[class*="stCard"]:hover,
    [data-testid="stDataFrame"]:hover,
    div.stAlert:hover {{
        transform: translateY(-5px);
        box-shadow: 0 12px 30px rgba(0,0,0,0.2);
    }}

    /* ---------- BUTTONS ---------- */
    .stButton>button {{
        background-color: #0b3c5d;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        font-size: 16px;
        padding: 10px 20px;
        margin: 5px;
        transition: all 0.3s;
    }}
    .stButton>button:hover {{
        background-color: #09324d;
        transform: scale(1.05);
    }}

    /* ---------- HEADINGS ---------- */
    h1, h2, h3 {{
        color: #0b3c5d;
    }}

    /* ---------- SIDEBAR ---------- */
    section[data-testid="stSidebar"] {{
        background: rgba(233, 239, 245, 0.9);
        border-radius: 12px;
        padding: 15px;
    }}

    /* ---------- ALERT BOX COLORS ---------- */
    div.stAlert.stAlertInfo,
    div.stAlert.stAlertSuccess {{
        background-color: #f0f2f6 !important;
        color: #0b3c5d !important;
        border: 1px solid #d1d5db !important;
        border-radius: 12px;
        padding: 15px;
    }}

    div.stAlert.stAlertWarning {{
        background-color: rgba(255, 255, 200, 0.85) !important;
        color: #856404 !important;
        border-radius: 12px;
        padding: 15px;
    }}
    /* ---------- UNREAD EMAIL BOX ---------- */
    .email-box {{
        background-color: #f0f2f6;
        color: #0b3c5d;
        padding: 18px;
        border-radius: 14px;
        border-left: 6px solid #0b3c5d;
        box-shadow: 0 6px 15px rgba(0,0,0,0.15);
        margin-bottom: 15px;
        max-width: 70%;
    }}

    </style>
    """, unsafe_allow_html=True)

# Call background
set_bg("static/bg.jpeg")

# ---------- TITLE ----------
st.title("📧 CivicEye – Email-Based Complaint Analysis")

CSV_FILE = "emails.csv"
if "all_emails" not in st.session_state:
    st.session_state.all_emails = []
if "unread_emails" not in st.session_state:
    st.session_state.unread_emails = []

import re

def clean_email_body(text):
    if not text:
        return ""
    text = html.unescape(text)          # decode HTML entities
    text = re.sub(r'<.*?>', '', text)   # remove HTML tags
    text = text.replace("*/", "")
    return text.strip()



# ---------------- FETCH EMAILS FUNCTION ----------------
def fetch_emails(unread_only=True):
    emails = []

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login("civiceye463@gmail.com", "bgos csgv uwqd bbhl")
    mail.select("inbox")

    criteria = "(UNSEEN)" if unread_only else "ALL"
    _, messages = mail.search(None, criteria)

    for mail_id in messages[0].split():
        _, msg_data = mail.fetch(mail_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        subject = msg["subject"]
        sender = msg.get("From")

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        emails.append({
            "mail_id": mail_id,
            "sender": sender,
            "subject": subject,
            "body": body
        })

    return emails, mail

# ---------------- INITIALIZE SESSION STATE ----------------
if os.path.exists(CSV_FILE):
    st.session_state.all_emails = pd.read_csv(CSV_FILE).to_dict("records")
else:
    st.session_state.all_emails = []

st.session_state.complaints = st.session_state.all_emails


# ---------------- FETCH EMAILS BUTTON ----------------
if st.button("📩 Fetch Emails"):
    with st.spinner("Fetching emails..."):
        unread_emails, mail = fetch_emails(unread_only=True)
        st.session_state.unread_emails = unread_emails

        if unread_emails:
            for e in unread_emails:
                st.markdown(f"""
                <div class="email-box">
                    <b>From:</b> {e['sender']}<br><br>
                    <b>Subject:</b> {e['subject']}<br><br>
                    <b>Body:</b><br>
                    <pre style="white-space: pre-wrap; font-family: inherit;">
                    {clean_email_body(e['body'])}
                    </pre>
                </div>
                """, unsafe_allow_html=True)

                mail.store(e["mail_id"], "+FLAGS", "\\Seen")
        else:
            st.info("No unread emails.")

        mail.logout()

        all_emails, _ = fetch_emails(unread_only=False)

    new_count = 0
    existing_ids = [c["id"] for c in st.session_state.all_emails]

    for e in all_emails:
        complaint_id = e["sender"] + "||" + e["subject"]
        if complaint_id in existing_ids:
            continue

        text = e["subject"] + " " + e["body"]
        result = predict_complaint(text)

        st.session_state.all_emails.append({
            "id": complaint_id,
            "sender": e["sender"],
            "subject": e["subject"],
            "body": e["body"],
            "category": result["category"],
            "priority": result["priority"]
        })
        new_count += 1

    pd.DataFrame(st.session_state.all_emails).to_csv(CSV_FILE, index=False)
    st.session_state.complaints = st.session_state.all_emails

    st.success(f"{new_count} new email(s) stored.")



# ---------------- COMPLAINT TABLE ----------------
# ---------------- COMPLAINT TABLE ----------------
st.markdown("### 🗂 Complaint Table")

if st.session_state.complaints:
    hide_non_civic = st.checkbox("Hide non-civic emails", value=True)
    filter_priority = st.selectbox("Filter by Priority", ["All", "High", "Medium", "Low"])
    filter_category = st.text_input("Filter by Category keyword", placeholder="e.g., Water, Road")

    table_placeholder = st.empty()   # ✅ PLACEHOLDER AFTER FILTERS

    filtered_source = st.session_state.complaints
    if hide_non_civic:
        filtered_source = [
            c for c in filtered_source
            if str(c.get("category", "")).lower() != "not a civic complaint"
        ]

    filtered = []
    for c in filtered_source:
        if filter_priority != "All" and str(c.get("priority", "")).lower() != filter_priority.lower():
            continue
        if filter_category.strip():
            text = (
                str(c.get("subject", "")) +
                str(c.get("body", "")) +
                str(c.get("category", ""))
            ).lower()
            if filter_category.lower() not in text:
                continue
        filtered.append(c)

    if filtered:
        df = pd.DataFrame(filtered)

        if "is_unread" in df.columns:
            df = df.drop(columns=["is_unread"])

        table_placeholder.dataframe(df, height=300)
    else:
        table_placeholder.warning("No complaints match the filter.")
else:
    st.info("No complaints submitted yet.")

# ---------------- COMPLAINT CHARTS ----------------
st.markdown("### 📊 Complaint Charts")
if st.session_state.complaints:
    chart_data = pd.DataFrame(st.session_state.complaints)

# Priority Pie Chart
st.markdown("#### Complaint Summary by Priority")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    priority_counts = chart_data["priority"].value_counts()

    fig1, ax1 = plt.subplots(figsize=(3, 3))
    ax1.pie(
        priority_counts,
        labels=priority_counts.index,
        autopct="%1.1f%%",
        startangle=140,
        textprops={"fontsize": 8}
    )
    ax1.axis("equal")

    st.pyplot(fig1, use_container_width=False)
    plt.close(fig1)

# Category Pie Chart
if not chart_data["category"].isnull().all():
    st.markdown("#### Complaint Summary by Category")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        category_counts = chart_data["category"].value_counts()

        fig2, ax2 = plt.subplots(figsize=(3, 3))

        wedges, texts, autotexts = ax2.pie(
            category_counts,
            autopct="%1.1f%%",
            startangle=140,
            textprops={"fontsize": 4}
        )

        ax2.axis("equal")

        # 🔹 Legend instead of labels (prevents shrinking)
        ax2.legend(
            wedges,
            category_counts.index,
            title="Categories",
            loc="center left",
            bbox_to_anchor=(1.05, 0.5),
            fontsize=8
        )

        st.pyplot(fig2, use_container_width=False)
        plt.close(fig2)



else:
    st.info("No complaints submitted yet.")

