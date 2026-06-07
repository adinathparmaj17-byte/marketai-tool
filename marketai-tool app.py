# ============================================================
# RealtyReach - WhatsApp Campaign Tool for Real Estate Agents
# Lean SaaS MVP Version
# ============================================================

import streamlit as st
import pandas as pd
import os
import json
import re
import urllib.parse
from datetime import datetime, timedelta

st.set_page_config(page_title="RealtyReach", layout="wide")

# -------------------------
# CONFIG
# -------------------------

TRIAL_DAYS = 7
TRIAL_CONTACT_LIMIT = 200

USERS_FILE = "users.json"

# -------------------------
# HELPERS
# -------------------------

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email)

def clean_mobile(num):
    num = re.sub(r"\D", "", str(num))
    if len(num) == 10:
        return "91" + num
    return num

def generate_whatsapp_link(mobile, message):
    return f"https://wa.me/{clean_mobile(mobile)}?text={urllib.parse.quote(message)}"

# -------------------------
# SESSION INIT
# -------------------------

for key in ["logged_in", "user_id", "campaign_data"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ============================================================
# AUTH SECTION
# ============================================================

if not st.session_state["logged_in"]:

    st.title("🏡 RealtyReach")
    st.subheader("Send Personalized Property Updates via WhatsApp")

    tab1, tab2 = st.tabs(["Login", "Start Free Trial"])

    users = load_users()

    # LOGIN
    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if email in users and users[email]["password"] == password:
                st.session_state["logged_in"] = True
                st.session_state["user_id"] = email
                st.rerun()
            else:
                st.error("Invalid credentials")

    # SIGNUP
    with tab2:
        name = st.text_input("Your Name")
        email = st.text_input("Email Address")
        password = st.text_input("Create Password", type="password")

        if st.button("Start 7-Day Free Trial"):
            if not validate_email(email):
                st.error("Enter valid email")
            elif email in users:
                st.error("Email already exists")
            else:
                trial_start = datetime.now()
                trial_end = trial_start + timedelta(days=TRIAL_DAYS)

                users[email] = {
                    "name": name,
                    "password": password,
                    "trial_start": trial_start.isoformat(),
                    "trial_end": trial_end.isoformat(),
                    "plan": "trial"
                }

                save_users(users)
                st.success("Account created! Please login.")

    st.stop()

# ============================================================
# USER DASHBOARD
# ============================================================

users = load_users()
user = users[st.session_state["user_id"]]

trial_end = datetime.fromisoformat(user["trial_end"])
days_left = (trial_end - datetime.now()).days

if user["plan"] == "trial" and datetime.now() > trial_end:
    st.error("Your trial has expired. Please contact us to upgrade.")
    st.stop()

# HEADER
col1, col2 = st.columns([0.8, 0.2])
with col1:
    st.title("🏡 RealtyReach Dashboard")
    st.caption(f"Welcome {user['name']}")

with col2:
    if st.button("Logout"):
        st.session_state["logged_in"] = None
        st.session_state["user_id"] = None
        st.rerun()

if user["plan"] == "trial":
    st.info(f"Trial active — {max(days_left,0)} days remaining")

# ============================================================
# CREATE CAMPAIGN
# ============================================================

st.subheader("📢 Create WhatsApp Campaign")

campaign_name = st.text_input("Campaign Name")
message_template = st.text_area(
    "Message Template",
    value="Hi {{name}},\n\nNew property available in your area. Let me know if you're interested!"
)

uploaded_file = st.file_uploader("Upload Buyer Excel (Name, Mobile)", type=["csv", "xlsx"])

if uploaded_file:

    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith("csv") else pd.read_excel(uploaded_file)

    df.columns = [c.lower() for c in df.columns]

    if "name" not in df.columns or "mobile" not in df.columns:
        st.error("Excel must contain 'Name' and 'Mobile' columns")
        st.stop()

    if user["plan"] == "trial" and len(df) > TRIAL_CONTACT_LIMIT:
        st.error(f"Trial limit is {TRIAL_CONTACT_LIMIT} contacts")
        st.stop()

    st.success(f"{len(df)} contacts loaded")

    preview = df.head(5)
    st.dataframe(preview)

    if st.button("Generate WhatsApp Links"):

        links = []

        for _, row in df.iterrows():
            name = str(row["name"])
            mobile = str(row["mobile"])

            msg = message_template.replace("{{name}}", name)
            link = generate_whatsapp_link(mobile, msg)

            links.append({
                "Name": name,
                "Mobile": mobile,
                "WhatsApp Link": link
            })

        export_df = pd.DataFrame(links)
        csv = export_df.to_csv(index=False)

        st.success("Links generated successfully!")

        st.download_button(
            "Download WhatsApp Link File",
            data=csv,
            file_name=f"{campaign_name}_whatsapp_links.csv",
            mime="text/csv"
        )

# ============================================================
# UPGRADE SECTION
# ============================================================

st.divider()
st.subheader("🚀 Upgrade to Pro")

st.markdown("""
**Pro Plan – ₹499/month**

✅ Unlimited contacts  
✅ Unlimited campaigns  
✅ Priority support  

To upgrade:
Send payment via UPI to: yourupi@bank  
Then email screenshot to: your@email.com  
""")
