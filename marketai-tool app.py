# ============================================================
#  MarketAI - Free WhatsApp & Email Marketing Tool
#  HUMAN-LIKE SENDING MODE  -  Anti-Spam by Design
#  WITH USER AUTHENTICATION & SENDER IDENTIFICATION
# ============================================================
#  Features:
#  - Sign Up (Register new account with Email or Mobile)
#  - Login (via Email OR Mobile Number)
#  - Random delays between messages (30-120 sec like a real person)
#  - Message variations (not identical copies)
#  - Random emoji shuffling
#  - Batch limits per hour
#  - Business hours only option
#  - CUSTOMERS SEE WHO SENT THE MESSAGE

import pandas as pd
import streamlit as st
import time
import re
import os
import random
import urllib.parse
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

# ─── Page Config ────────────────────────────────────
st.set_page_config(page_title="MarketAI - Human-Like Sender", page_icon="🤖", layout="wide")

# ─── USER AUTHENTICATION ─────────────────────────────
def load_users():
    """Load users from JSON file"""
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    """Save users to JSON file"""
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)

def validate_phone(phone):
    """Validate Indian mobile number"""
    phone = re.sub(r'[\s\-\+\(\)]', '', str(phone))
    if phone.startswith("91") and len(phone) == 12:
        return phone
    elif phone.startswith("0") and len(phone) == 11:
        return "91" + phone[1:]
    elif len(phone) == 10:
        return "91" + phone
    return None

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def signup_user(email, mobile, password, business_name):
    """Sign up (Register) a new user"""
    users = load_users()
    
    # Validate inputs
    if not business_name or len(business_name.strip()) < 2:
        return False, "❌ Business name must be at least 2 characters"
    
    if email:
        if not validate_email(email):
            return False, "❌ Invalid email format"
        if email in users:
            return False, "❌ Email already registered"
    
    if mobile:
        clean_mobile = validate_phone(mobile)
        if not clean_mobile:
            return False, "❌ Invalid mobile number"
        # Check if mobile already exists
        for user_data in users.values():
            if user_data.get("mobile") == clean_mobile:
                return False, "❌ Mobile number already registered"
        mobile = clean_mobile
    
    if not email and not mobile:
        return False, "❌ Please provide either email or mobile number"
    
    if not password or len(password) < 6:
        return False, "❌ Password must be at least 6 characters"
    
    # Create user entry
    user_id = email if email else mobile
    users[user_id] = {
        "password": password,
        "email": email,
        "mobile": mobile,
        "business_name": business_name.strip(),
        "created": datetime.now().isoformat()
    }
    save_users(users)
    return True, "✅ Sign up successful! Now login with your credentials."

def login_user(identifier, password):
    """Login with Email OR Mobile Number"""
    users = load_users()
    
    if not identifier or not password:
        return False, None, "❌ Please enter both identifier and password"
    
    # Check if identifier is email
    if validate_email(identifier):
        if identifier in users and users[identifier]["password"] == password:
            return True, identifier, "✅ Login successful!"
        else:
            return False, None, "❌ Invalid email or password"
    
    # Check if identifier is mobile
    clean_mobile = validate_phone(identifier)
    if clean_mobile:
        for user_id, user_data in users.items():
            if user_data.get("mobile") == clean_mobile and user_data["password"] == password:
                return True, user_id, "✅ Login successful!"
        return False, None, "❌ Invalid mobile number or password"
    
    return False, None, "❌ Please enter valid email or mobile number"

def get_user_data(user_id):
    """Get user business data"""
    users = load_users()
    return users.get(user_id, {})

# ─── SESSION State ──────────────────────────────────
for v in ["logged_in", "user_id", "customers", "sent_log", "sending_active", "uploaded_filename"]:
    if v not in st.session_state:
        if v == "customers":
            st.session_state[v] = []
        elif v == "sent_log":
            st.session_state[v] = []
        else:
            st.session_state[v] = None if v != "sending_active" else False

# ─── ANTI-SPAM / HUMAN-LIKE CONFIG ─────────────────
HUMAN_DELAY_MIN = 30      # Min seconds between messages
HUMAN_DELAY_MAX = 120     # Max seconds between messages
BUSINESS_HOURS_START = 9   # 9 AM
BUSINESS_HOURS_END = 20    # 8 PM

GREETINGS = [
    "Hi {name}!", "Hello {name},", "Hey {name}!",
    "Hi there {name}!", "Hello {name} 👋", "Hey {name} 🙌",
    "Hi {name}, hope you're doing well!",
    "Hello {name}, hope this finds you well!",
]

# ─── Helper Functions ───────────────────────────────

def validate_excel(df):
    df.columns = [str(c).strip().lower() for c in df.columns]
    mapping = {}
    for col in df.columns:
        if "name" in col or "customer" in col:
            mapping[col] = "name"
        elif any(x in col for x in ["mobile", "phone", "contact", "whatsapp", "number"]):
            mapping[col] = "mobile"
        elif "email" in col:
            mapping[col] = "email"
    has_name = "name" in mapping.values()
    has_mobile = "mobile" in mapping.values()
    has_email = "email" in mapping.values()
    if not has_name:
        return False, "No 'Name' column found", mapping
    if not has_mobile and not has_email:
        return False, "Need 'Mobile' or 'Email' column", mapping
    return True, "Excel looks good!", mapping

def clean_mobile(num):
    num = re.sub(r'[\s\-\+\(\)]', '', str(num))
    if num.startswith("91") and len(num) == 12:
        return num
    elif num.startswith("0") and len(num) == 11:
        return "91" + num[1:]
    elif len(num) == 10:
        return "91" + num
    return num

def generate_whatsapp_link(mobile, message):
    clean_num = clean_mobile(mobile)
    return f"https://wa.me/{clean_num}?text={urllib.parse.quote(message)}"

def save_customers(df, mapping):
    customers = []
    for idx, row in df.iterrows():
        nc = [k for k, v in mapping.items() if v == "name"][0]
        name = str(row[nc]).strip()
        mobile = ""
        mc = [k for k, v in mapping.items() if v == "mobile"]
        if mc:
            mobile = str(row[mc[0]]).strip()
        email = ""
        ec = [k for k, v in mapping.items() if v == "email"]
        if ec:
            email = str(row[ec[0]]).strip()
        if name.lower() in ["nan", "nat", "", "none"]:
            name = f"Customer {idx+1}"
        customers.append({
            "id": idx, "name": name,
            "mobile": mobile if mobile.lower() not in ["nan","nat","","none"] else "",
            "email": email if email.lower() not in ["nan","nat","","none"] else "",
            "whatsapp_sent": False, "email_sent": False,
            "whatsapp_link": "", "email_content": "", "email_subject": "",
            "sent_at": None
        })
    return customers

def randomize_message(template, name, sender_name):
    """Add human-like variation so each message is slightly different."""
    greeting = random.choice(GREETINGS).format(name=name)
    msg = template.replace("{{name}}", name)
    msg = msg.replace("{{sender}}", sender_name)
    # Sometimes swap the greeting
    if msg.startswith("Hi") or msg.startswith("Hello") or msg.startswith("Hey"):
        lines = msg.split("\n", 1)
        if len(lines) > 1:
            msg = greeting + "\n" + lines[1]
    # Add sender signature
    msg = msg.strip() + f"\n\n— {sender_name}"
    # Randomly add emoji
    if random.random() > 0.4:
        emojis = ["🎉", "🔥", "💥", "✨", "🎊", "🚀", "💪", "👋", "⭐", "🎯"]
        msg = msg + " " + random.choice(emojis)
    return msg

def randomize_email(template, name, subject, sender_name):
    """Add slight variations to email with sender info."""
    greeting = random.choice(GREETINGS).format(name=name)
    if random.random() > 0.5:
        emojis = ["🎉", "🔥", "✨", "🚀", "💌", "📢"]
        subject = random.choice(emojis) + " " + subject
    body = template.replace("{{name}}", name)
    body = body.replace("{{sender}}", sender_name)
    body = body.replace("Hi {{name}}", greeting)
    subject = subject.replace("{{name}}", name)
    # Add sender to email footer
    body = body + f"\n\n<p><strong>Sent by: {sender_name}</strong></p>"
    return subject, body

def get_human_delay():
    return random.randint(HUMAN_DELAY_MIN, HUMAN_DELAY_MAX)

def is_business_hours():
    now = datetime.now()
    return BUSINESS_HOURS_START <= now.hour < BUSINESS_HOURS_END

def get_batch_stats(customers):
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sent_hr = sum(1 for c in customers if c.get("sent_at") and c["sent_at"] > one_hour_ago)
    sent_day = sum(1 for c in customers if c.get("sent_at") and c["sent_at"] > today_start)
    return sent_hr, sent_day

# ─── AUTHENTICATION PAGE ─────────────────────────────
if not st.session_state["logged_in"]:
    st.title("🤖 MarketAI - Authentication")
    st.markdown("**Welcome to MarketAI - Human-Like Marketing Sender**")
    
    tab1, tab2 = st.tabs(["🔓 Login", "📝 Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        st.info("💡 Login with either your **Email** or **Mobile Number**")
        
        login_identifier = st.text_input(
            "📧 Email or 📱 Mobile Number",
            placeholder="example@email.com or 9876543210",
            key="login_identifier"
        )
        login_password = st.text_input("🔐 Password", type="password", key="login_pass")
        
        if st.button("Login", use_container_width=True, type="primary"):
            if login_identifier and login_password:
                success, user_id, msg = login_user(login_identifier, login_password)
                if success:
                    st.session_state["logged_in"] = True
                    st.session_state["user_id"] = user_id
                    st.success(msg)
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("❌ Please enter both email/mobile and password")
    
    with tab2:
        st.subheader("Create New Account")
        st.info("📋 Fill in your details to sign up")
        
        signup_business = st.text_input("🏢 Business Name *", placeholder="Your Company/Business Name", key="reg_business")
        signup_email = st.text_input("📧 Email (optional)", placeholder="you@example.com", key="reg_email")
        signup_mobile = st.text_input("📱 Mobile Number (optional)", placeholder="9876543210", key="reg_mobile")
        st.caption("⚠️ Provide at least Email or Mobile Number")
        
        signup_password = st.text_input("🔐 Create Password *", type="password", key="reg_pass")
        signup_confirm = st.text_input("🔐 Confirm Password *", type="password", key="reg_pass_confirm")
        
        if st.button("Sign Up", use_container_width=True, type="primary"):
            if not signup_business:
                st.error("❌ Business name is required")
            elif not signup_email and not signup_mobile:
                st.error("❌ Please provide at least Email or Mobile Number")
            elif signup_password != signup_confirm:
                st.error("❌ Passwords don't match")
            else:
                success, msg = signup_user(signup_email, signup_mobile, signup_password, signup_business)
                if success:
                    st.success(msg)
                    st.info("👈 Go to **Login** tab and login with your credentials")
                else:
                    st.error(msg)
    
    st.divider()
    st.markdown("""
    <div style="text-align:center;color:gray;font-size:12px;">
    🤖 MarketAI - Send messages with human-like behavior<br>
    ✅ **Sign Up**: Register with Email or Mobile Number<br>
    ✅ **Login**: Use Email or Mobile Number (NO verification code needed)<br>
    ✅ Excel upload, delete & message sending with sender identification
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─── LOGGED IN USER AREA ────────────────────────────
user_data = get_user_data(st.session_state["user_id"])
sender_name = user_data.get("business_name", "Your Business")
user_identifier = user_data.get("email") or user_data.get("mobile")

# Logout button in top right
col1, col2 = st.columns([0.85, 0.15])
with col2:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["user_id"] = None
        st.session_state["customers"] = []
        st.rerun()

# ─── SIDEBAR ────────────────────────────────────────
st.sidebar.title(f"🤖 MarketAI")
st.sidebar.markdown(f"**{sender_name}**")
st.sidebar.caption(f"📧/📱 {user_identifier}")
st.sidebar.divider()

st.sidebar.header("📁 Step 1: Upload Excel")
uploaded_file = st.sidebar.file_uploader("Choose file", type=["xlsx", "xls", "csv"])

if uploaded_file:
    st.sidebar.success(f"📄 {uploaded_file.name}")
    if st.sidebar.button("🗑️ Delete Uploaded File", use_container_width=True):
        st.session_state["customers"] = []
        st.session_state["uploaded_filename"] = None
        st.session_state["sent_log"] = []
        st.sidebar.success("✅ File deleted! Ready to upload new file.")
        st.rerun()

st.sidebar.header("🔧 Step 2: Templates")
with st.sidebar.expander("📝 Messages", expanded=True):
    whatsapp_template = st.text_area(
        "WhatsApp:", value="Hi {{name}},\n\nThis is a special offer just for you!\n\nVisit us today and get 20% OFF.\n\nReply STOP to opt out.",
        height=120, help="Use {{name}} for customer name and {{sender}} for your business name"
    )
    email_subject = st.text_input("Email Subject:", value="Special Offer Just for You, {{name}}!")
    email_body = st.text_area(
        "Email Body (HTML):",
        value="""<h2>Hi {{name}},</h2>
<p>We have an <strong>exclusive offer</strong> just for you!</p>
<p>Get <strong>20% OFF</strong> on your next purchase.</p>
<p><a href="https://yourwebsite.com/offer">Click here to claim</a></p>
<br><p>Best regards,<br>{{sender}}</p>""",
        height=150, help="Use {{name}} and {{sender}} placeholders"
    )

st.sidebar.header("⚙️ Step 3: Anti-Spam Settings")
with st.sidebar.expander("🧠 Human-Like Behavior", expanded=True):
    st.info("These settings prevent spam flags & account bans.")
    
    human_delay_min = st.slider("Min delay (sec):", 10, 300, 30, 5,
        help="30+ sec recommended. Lower = more risk of ban.")
    human_delay_max = st.slider("Max delay (sec):", 30, 600, 120, 10,
        help="60-120 sec = natural human pace.")
    
    max_per_hour = st.slider("Max per hour:", 5, 50, 20, 5,
        help="Real humans send ~10-20 msgs/hour max.")
    max_per_day = st.slider("Max per day:", 10, 200, 80, 10)
    
    use_business_hours = st.checkbox("Only 9AM-8PM (business hours)", True)
    add_variations = st.checkbox("Random variations per message ✅", True,
        help="Each customer gets slightly different wording")

with st.sidebar.expander("💬 WhatsApp", expanded=False):
    whatsapp_method = st.radio("Method:", [
        "Generate wa.me links (click manually - SAFEST)",
        "PyWhatKit automation (risk of ban)"
    ])

with st.sidebar.expander("📧 Email", expanded=True):
    email_method = st.radio("Send via:", [
        "Generate mailto links (click manually)",
        "SMTP with delays (Gmail - Free)",
        "Brevo API with delays (300/day)"
    ])
    if "SMTP" in email_method:
        smtp_server = st.selectbox("Server", ["smtp.gmail.com", "smtp.office365.com"])
        smtp_port = st.number_input("Port", 587)
        smtp_user = st.text_input("Your Email", placeholder="you@gmail.com")
        smtp_pass = st.text_input("App Password", type="password")
    elif "Brevo" in email_method:
        brevo_api = st.text_input("Brevo API Key", type="password")
        sender_email = st.text_input("Sender Email", placeholder="you@yourdomain.com")

# ─── MAIN AREA ──────────────────────────────────────
st.title(f"🤖 MarketAI — {sender_name}")
st.markdown("""
**Sends like a human, not a spam bot.**  
Random delays • Different wording per customer • Rate limited • Business hours aware  
Unlike AiSensy/WATI which blast instantly — this mimics **real human sending behavior** to protect your account.

**🎯 KEY FEATURES:**
- ✅ **Customers see WHO sent the message** — Your Business Name appears in every message!
- ✅ **File Upload & Delete** — Easy Excel file management
- ✅ **Email or Mobile Login** — Simple authentication, no phone verification needed
- ✅ **Message Personalization** — Each customer gets unique variations
""")

# Upload
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        is_valid, msg, mapping = validate_excel(df)
        if is_valid:
            st.success(msg)
            with st.expander("📊 Preview (First 10)", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)
                st.caption(f"Total: {len(df)} rows")
            if st.button("📥 Load Customers", use_container_width=True):
                st.session_state["customers"] = save_customers(df, mapping)
                st.session_state["sent_log"] = []
                st.session_state["sending_active"] = False
                st.session_state["uploaded_filename"] = uploaded_file.name
                st.success(f"Loaded {len(st.session_state['customers'])} customers!")
                st.rerun()
        else:
            st.error(msg)
            st.write("Found columns:", list(df.columns))
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("👈 Upload your Excel/CSV from sidebar.")
    with st.expander("📋 Required Columns"):
        st.dataframe(pd.DataFrame({
            "Customer Name": ["Rahul S.", "Priya M."],
            "Mobile Number": ["9876543210", "9123456789"],
            "Email Address": ["rahul@email.com", "priya@email.com"]
        }), use_container_width=True)

# ─── CUSTOMER LIST ─────────────────────────────────
if st.session_state["customers"]:
    st.divider()
    customers = st.session_state["customers"]
    total = len(customers)
    wa_sent = sum(1 for c in customers if c["whatsapp_sent"])
    em_sent = sum(1 for c in customers if c["email_sent"])
    remaining = total - max(wa_sent, em_sent)
    last_hour, today = get_batch_stats(customers)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 Total", total)
    c2.metric("💬 WA Sent", wa_sent)
    c3.metric("📧 Email Sent", em_sent)
    c4.metric("⏳ Remaining", remaining)
    c5.metric("📊 /hr Limit", f"{last_hour}/{max_per_hour}")

    if last_hour >= max_per_hour:
        st.warning(f"⚠️ Hourly limit hit! Wait before sending more.")
    if today >= max_per_day:
        st.error(f"🚫 Daily limit reached ({today}/{max_per_day}).")
    if use_business_hours and not is_business_hours():
        st.warning(f"🌙 Outside business hours (9AM-8PM). Auto-send paused.")

    # ─── HUMAN-LIKE SENDING ENGINE ────────────────
    st.subheader("🎯 Human-Like Sending Controls")

    col_a, col_b, col_c, col_d = st.columns(4)

    with col_a:
        if not st.session_state["sending_active"]:
            if st.button("▶️ START Human-Like Sending", use_container_width=True, type="primary"):
                if last_hour >= max_per_hour:
                    st.error("Rate limit reached!")
                    st.stop()
                if today >= max_per_day:
                    st.error("Daily limit reached!")
                    st.stop()
                if use_business_hours and not is_business_hours():
                    st.error("Outside business hours!")
                    st.stop()
                st.session_state["sending_active"] = True
                st.rerun()
        else:
            if st.button("⏹️ STOP", use_container_width=True, type="secondary"):
                st.session_state["sending_active"] = False
                st.rerun()

    with col_b:
        if st.button("🔗 Generate WA Links", use_container_width=True):
            for c in st.session_state["customers"]:
                if c["mobile"] and not c["whatsapp_sent"]:
                    msg = randomize_message(whatsapp_template, c["name"], sender_name)
                    c["whatsapp_link"] = generate_whatsapp_link(c["mobile"], msg)
            st.success("Links generated!")
            st.rerun()

    with col_c:
        if st.button("✉️ Prepare Emails", use_container_width=True):
            for c in st.session_state["customers"]:
                if c["email"] and not c["email_sent"]:
                    subj, body = randomize_email(email_body, c["name"], email_subject, sender_name)
                    plain = re.sub(r'<[^>]+>', '', body).strip()
                    c["email_subject"] = subj
                    c["email_content"] = plain
            st.success("Emails prepared!")
            st.rerun()

    with col_d:
        if st.button("📥 Export CSV", use_container_width=True):
            rows = [{
                "Name": c["name"], "Mobile": c["mobile"], "Email": c["email"],
                "WhatsApp_Link": c.get("whatsapp_link", ""),
                "WhatsApp_Sent": c["whatsapp_sent"], "Email_Sent": c["email_sent"],
                "Sent_At": str(c.get("sent_at", ""))
            } for c in st.session_state["customers"]]
            export_df = pd.DataFrame(rows)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fn = f"report_{ts}.csv"
            export_df.to_csv(fn, index=False)
            with open(fn, "rb") as f:
                st.download_button("📥 Download", data=f, file_name=fn, mime="text/csv", use_container_width=True)

    # ─── THE HUMAN-LIKE SENDING LOOP ──────────────────
    if st.session_state["sending_active"]:
        lh, td = get_batch_stats(st.session_state["customers"])
        if lh >= max_per_hour:
            st.error(f"⛔ Hourly limit. Stopping.")
            st.session_state["sending_active"] = False
            st.rerun()
        if td >= max_per_day:
            st.error(f"⛔ Daily limit. Stopping.")
            st.session_state["sending_active"] = False
            st.rerun()
        if use_business_hours and not is_business_hours():
            st.warning("🌙 Outside hours. Pausing.")
            st.session_state["sending_active"] = False
            st.rerun()

        # Find next unsent customer
        next_c = None
        for c in st.session_state["customers"]:
            if not c["whatsapp_sent"] and c["mobile"]:
                next_c = c
                break
        if next_c is None:
            for c in st.session_state["customers"]:
                if not c["email_sent"] and c["email"]:
                    next_c = c
                    break

        if next_c is None:
            st.success("✅ All done! Human-like sending complete.")
            st.session_state["sending_active"] = False
            st.rerun()

        c = next_c
        with st.container(border=True):
            st.info(f"📤 **Now sending to: {c['name']}** (from **{sender_name}**)")

            if c["mobile"] and not c["whatsapp_sent"]:
                with st.spinner(f"💬 Preparing WhatsApp for {c['name']}..."):
                    msg = randomize_message(whatsapp_template, c["name"], sender_name) if add_variations else whatsapp_template.replace("{{name}}", c["name"]).replace("{{sender}}", sender_name)
                    c["whatsapp_link"] = generate_whatsapp_link(c["mobile"], msg)
                    with st.expander("📱 Message Preview", expanded=False):
                        st.text(msg)
                    delay = get_human_delay()
                    st.caption(f"⏳ Human-like delay: {delay}s (thinking + typing)...")
                    prog = st.progress(0)
                    for i in range(100):
                        time.sleep(delay / 100)
                        prog.progress(i + 1)
                    c["whatsapp_sent"] = True
                    c["sent_at"] = datetime.now()
                    st.success(f"✅ WhatsApp ready for {c['name']} — Click 💬 button to send")
                    st.session_state["sent_log"].append({
                        "name": c["name"], "type": "WhatsApp",
                        "time": datetime.now().strftime("%H:%M:%S"), "delay": delay,
                        "sender": sender_name
                    })

            elif c["email"] and not c["email_sent"]:
                with st.spinner(f"📧 Preparing email for {c['name']}..."):
                    if add_variations:
                        subj, body = randomize_email(email_body, c["name"], email_subject, sender_name)
                    else:
                        subj = email_subject.replace("{{name}}", c["name"])
                        body = email_body.replace("{{name}}", c["name"]).replace("{{sender}}", sender_name)
                    plain = re.sub(r'<[^>]+>', '', body).strip()
                    c["email_subject"] = subj
                    c["email_content"] = plain

                    sent_via = ""
                    # Auto-send via SMTP
                    if "SMTP" in email_method and smtp_user and smtp_pass:
                        try:
                            m = MIMEMultipart("alternative")
                            m["From"] = f"{sender_name} <{smtp_user}>"
                            m["To"] = c["email"]
                            m["Subject"] = subj
                            m.attach(MIMEText(plain, "plain"))
                            m.attach(MIMEText(body, "html"))
                            server = smtplib.SMTP(smtp_server, int(smtp_port))
                            server.starttls()
                            server.login(smtp_user, smtp_pass)
                            server.sendmail(smtp_user, c["email"], m.as_string())
                            server.quit()
                            sent_via = "via SMTP"
                        except Exception as e:
                            st.warning(f"SMTP failed: {e}")

                    elif "Brevo" in email_method and brevo_api:
                        try:
                            import requests
                            headers = {"accept": "application/json", "content-type": "application/json", "api-key": brevo_api}
                            payload = {
                                "sender": {"name": sender_name, "email": sender_email},
                                "to": [{"email": c["email"], "name": c["name"]}],
                                "subject": subj, "htmlContent": body, "textContent": plain
                            }
                            resp = requests.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers)
                            if resp.status_code in [200, 201]:
                                sent_via = "via Brevo"
                            else:
                                st.warning(f"Brevo error: {resp.status_code}")
                        except Exception as e:
                            st.warning(f"Brevo failed: {e}")

                    delay = get_human_delay()
                    st.caption(f"⏳ Human-like delay: {delay}s...")
                    prog = st.progress(0)
                    for i in range(100):
                        time.sleep(delay / 100)
                        prog.progress(i + 1)

                    c["email_sent"] = True
                    c["sent_at"] = datetime.now()
                    st.success(f"✅ Email {'sent' if sent_via else 'ready'} for {c['name']} {sent_via}")
                    st.session_state["sent_log"].append({
                        "name": c["name"], "type": f"Email {sent_via}" if sent_via else "Email ready",
                        "time": datetime.now().strftime("%H:%M:%S"), "delay": delay,
                        "sender": sender_name
                    })

        # Check limits and continue
        lh2, td2 = get_batch_stats(st.session_state["customers"])
        if lh2 >= max_per_hour:
            st.warning(f"⏸️ Hourly limit. Pausing.")
            st.session_state["sending_active"] = False
        if td2 >= max_per_day:
            st.warning(f"⏸️ Daily limit. Done.")
            st.session_state["sending_active"] = False

        st.rerun()

    # ─── CUSTOMER TABLE ──────────────────────────
    st.subheader("👥 Customer List")
    search = st.text_input("🔍 Search:", placeholder="Type name...")
    filtered = st.session_state["customers"]
    if search:
        filtered = [c for c in filtered if search.lower() in c["name"].lower()]

    for c in filtered:
        cols = st.columns([2, 2, 2, 1, 1])
        with cols[0]:
            st.markdown(f"**{c['name']}**")
        with cols[1]:
            icon = "✅" if c["whatsapp_sent"] else "⬜"
            st.markdown(f"📱 {c['mobile'] or '—'} {icon}")
        with cols[2]:
            icon = "✅" if c["email_sent"] else "⬜"
            st.markdown(f"📧 {c['email'] or '—'} {icon}")
        with cols[3]:
            if c["whatsapp_link"] and not c["whatsapp_sent"]:
                st.markdown(f'<a href="{c["whatsapp_link"]}" target="_blank"><button style="background:#25D366;color:white;border:none;padding:4px 10px;border-radius:5px;">💬 WA</button></a>', unsafe_allow_html=True)
        with cols[4]:
            if c["email"] and c.get("email_content") and not c["email_sent"]:
                link = f"mailto:{c['email']}?subject={urllib.parse.quote(c.get('email_subject',''))}&body={urllib.parse.quote(c.get('email_content',''))}"
                st.markdown(f'<a href="{link}" target="_blank"><button style="background:#EA4335;color:white;border:none;padding:4px 10px;border-radius:5px;">📧</button></a>', unsafe_allow_html=True)

    # ─── LOG ─────────────────────────────────────
    if st.session_state["sent_log"]:
        st.divider()
        st.subheader("📋 Sending Log")
        log_df = pd.DataFrame(st.session_state["sent_log"])
        st.dataframe(log_df, use_container_width=True, height=200)
        if st.button("🗑️ Clear Log"):
            st.session_state["sent_log"] = []
            st.rerun()

# ─── FOOTER ────────────────────────────────────────
st.divider()
st.markdown("""
<div style="text-align:center;padding:20px;color:gray;font-size:13px;">
    <strong>🤖 MarketAI — Human-Like Marketing Sender</strong><br>
    Free alternative to AiSensy / WATI | <strong>Anti-Spam by Design</strong><br>
    <span style="font-size:11px;">
    ✅ **Sign Up**: Register with Email or Mobile Number<br>
    ✅ **Login**: Use Email or Mobile Number (simple password authentication)<br>
    ✅ **Excel Upload & Delete**: Easy file management<br>
    ✅ **Customers See WHO Sent**: Your business name in every message<br>
    ✅ **Message Personalization**: Unique variations per customer<br>
    ⚠️ Always get opt-in consent. WhatsApp ban risk if sending too fast.<br>
    This tool enforces human-like speeds to protect your account.
    </span>
</div>
""", unsafe_allow_html=True)


