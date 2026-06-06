# ============================================================
#  MarketAI - 100% FREE WhatsApp & Email Marketing Tool
#  AUTO SENDING - Anti-Spam by Design
# ============================================================
#  Features:
#  - Sign Up with Country Code & Mobile Verification (OTP via SMS)
#  - Auto login to Gmail SMTP & PyWhatKit
#  - WhatsApp: PyWhatKit (100% FREE)
#  - Email: Gmail SMTP (100% FREE)
#  - WhatsApp Link generation in Excel
#  - Send messages one by one with delays

import pandas as pd
import streamlit as st
import time
import re
import os
import random
import json
import smtplib
import secrets
import string
import urllib.parse
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─── Page Config ────────────────────────────────────
st.set_page_config(page_title="MarketAI - 100% FREE Sender", page_icon="🤖", layout="wide")

# ─── OTP & VERIFICATION ──────────────────────────────
def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def save_otp_verification(phone, otp):
    """Save OTP to file for mobile verification"""
    try:
        if not os.path.exists("otp_data.json"):
            otp_data = {}
        else:
            with open("otp_data.json", "r") as f:
                otp_data = json.load(f)
        
        otp_expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
        otp_data[phone] = {
            "otp": otp,
            "expiry": otp_expiry,
            "created": datetime.now().isoformat()
        }
        
        with open("otp_data.json", "w") as f:
            json.dump(otp_data, f)
        return True
    except Exception as e:
        print(f"Save OTP error: {e}")
        return False

def load_otp_verification(phone):
    """Load OTP from file"""
    try:
        if not os.path.exists("otp_data.json"):
            return None, None
        
        with open("otp_data.json", "r") as f:
            otp_data = json.load(f)
        
        if phone in otp_data:
            return otp_data[phone]["otp"], otp_data[phone]["expiry"]
        return None, None
    except Exception as e:
        print(f"Load OTP error: {e}")
        return None, None

# ─── USER AUTHENTICATION ─────────────────────────────
def load_users():
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)

COUNTRY_CODES = {
    "🇮🇳 India": "+91",
    "🇵🇰 Pakistan": "+92",
    "🇧🇩 Bangladesh": "+880",
    "🇬🇧 UK": "+44",
    "🇺🇸 USA": "+1",
    "🇨🇦 Canada": "+1",
    "🇦🇺 Australia": "+61",
    "🇳🇿 New Zealand": "+64",
    "🇿🇦 South Africa": "+27",
    "🇩🇪 Germany": "+49",
    "🇫🇷 France": "+33",
    "🇮🇹 Italy": "+39",
    "🇪🇸 Spain": "+34",
    "🇸🇬 Singapore": "+65",
    "🇲🇾 Malaysia": "+60",
}

def validate_phone_with_country(country, phone):
    """Validate phone with country code"""
    phone = re.sub(r'[\s\-\+\(\)]', '', str(phone))
    country_code = COUNTRY_CODES.get(country, "").replace("+", "")
    
    if not country_code:
        return None, "Invalid country"
    
    if len(phone) < 8:
        return None, "Phone number too short"
    
    # Remove country code if user added it
    if phone.startswith(country_code):
        phone = phone[len(country_code):]
    
    return f"+{country_code}{phone}", "Valid"

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def signup_user_step1(email, country, phone, password, business_name, gmail_user, gmail_pass):
    """Step 1: Validate and generate OTP for mobile verification"""
    users = load_users()
    
    # Validate business name
    if not business_name or len(business_name.strip()) < 2:
        return False, "❌ Business name must be at least 2 characters"
    
    # Validate email
    if not validate_email(email):
        return False, "❌ Invalid email format"
    if email in users:
        return False, "❌ Email already registered"
    
    # Validate country and phone
    full_phone, phone_msg = validate_phone_with_country(country, phone)
    if not full_phone:
        return False, f"❌ {phone_msg}"
    
    # Check if phone already registered
    for user_data in users.values():
        if user_data.get("phone") == full_phone:
            return False, "❌ Phone number already registered"
    
    # Validate password
    if not password or len(password) < 6:
        return False, "❌ Password must be at least 6 characters"
    
    # Validate Gmail credentials
    if not gmail_user or not gmail_pass:
        return False, "❌ Please enter Gmail credentials"
    if not validate_email(gmail_user) or "gmail" not in gmail_user.lower():
        return False, "❌ Please use a Gmail account"
    
    # Generate OTP
    otp = generate_otp()
    
    # Save OTP to file
    if not save_otp_verification(full_phone, otp):
        return False, "❌ Error generating OTP. Please try again."
    
    # Store signup data in session
    st.session_state["signup_data"] = {
        "email": email,
        "country": country,
        "phone": full_phone,
        "password": password,
        "business_name": business_name.strip(),
        "gmail_user": gmail_user,
        "gmail_pass": gmail_pass,
    }
    
    return True, f"✅ OTP sent to {full_phone}\n\n📲 **Your OTP is: {otp}**\n\n(For demo - normally sent via SMS)"

def verify_otp(phone, otp_input):
    """Step 2: Verify OTP and create account"""
    users = load_users()
    signup_data = st.session_state.get("signup_data", {})
    
    # Load saved OTP
    saved_otp, otp_expiry = load_otp_verification(phone)
    
    if not saved_otp:
        return False, "❌ OTP not found. Please sign up again."
    
    # Check OTP expiry
    try:
        expiry_time = datetime.fromisoformat(otp_expiry)
        if datetime.now() > expiry_time:
            return False, "❌ OTP expired. Please sign up again."
    except:
        return False, "❌ Invalid OTP. Please sign up again."
    
    # Check OTP
    if str(otp_input).strip() != str(saved_otp).strip():
        return False, "❌ Invalid OTP"
    
    # Create user account
    user_id = signup_data.get("email")
    users[user_id] = {
        "password": signup_data.get("password"),
        "email": signup_data.get("email"),
        "country": signup_data.get("country"),
        "phone": phone,
        "business_name": signup_data.get("business_name"),
        "gmail_user": signup_data.get("gmail_user"),
        "gmail_pass": signup_data.get("gmail_pass"),
        "pywhatkit_enabled": True,
        "gmail_enabled": True,
        "created": datetime.now().isoformat()
    }
    save_users(users)
    
    # Clean up OTP
    if os.path.exists("otp_data.json"):
        with open("otp_data.json", "r") as f:
            otp_data = json.load(f)
        if phone in otp_data:
            del otp_data[phone]
        with open("otp_data.json", "w") as f:
            json.dump(otp_data, f)
    
    return True, "✅ Mobile verified! Account created successfully!"

def login_user(email, password):
    """Login with email"""
    users = load_users()
    
    if not email or not password:
        return False, None, "❌ Please enter email and password"
    
    if not validate_email(email):
        return False, None, "❌ Invalid email format"
    
    if email in users and users[email]["password"] == password:
        user_data = users[email]
        return True, email, f"✅ Welcome {user_data['business_name']}!"
    else:
        return False, None, "❌ Invalid email or password"

def get_user_data(user_id):
    users = load_users()
    return users.get(user_id, {})

# ─── SESSION State ──────────────────────────────────
for v in ["logged_in", "user_id", "customers", "sent_log", "sending_active", "signup_step", "signup_phone", "signup_data"]:
    if v not in st.session_state:
        if v == "customers":
            st.session_state[v] = []
        elif v == "sent_log":
            st.session_state[v] = []
        elif v == "signup_step":
            st.session_state[v] = 1
        else:
            st.session_state[v] = None if v != "sending_active" else False

# ─── CONFIG ─────────────────────────────────────
HUMAN_DELAY_MIN = 30
HUMAN_DELAY_MAX = 120
BUSINESS_HOURS_START = 9
BUSINESS_HOURS_END = 20

GREETINGS = [
    "Hi {name}!", "Hello {name},", "Hey {name}!",
    "Hi there {name}!", "Hello {name} 👋", "Hey {name} 🙌",
]

# ─── HELPER FUNCTIONS ───────────────────────────────

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
    """Generate WhatsApp link"""
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
            "whatsapp_link": "",
            "sent_at": None
        })
    return customers

def randomize_message(template, name, sender_name):
    greeting = random.choice(GREETINGS).format(name=name)
    msg = template.replace("{{name}}", name)
    msg = msg.replace("{{sender}}", sender_name)
    if msg.startswith("Hi") or msg.startswith("Hello") or msg.startswith("Hey"):
        lines = msg.split("\n", 1)
        if len(lines) > 1:
            msg = greeting + "\n" + lines[1]
    msg = msg.strip() + f"\n\n— {sender_name}"
    if random.random() > 0.4:
        emojis = ["🎉", "🔥", "💥", "✨", "🎊", "🚀", "💪", "👋", "⭐", "🎯"]
        msg = msg + " " + random.choice(emojis)
    return msg

def randomize_email(template, name, subject, sender_name):
    greeting = random.choice(GREETINGS).format(name=name)
    if random.random() > 0.5:
        emojis = ["🎉", "🔥", "✨", "🚀", "💌", "📢"]
        subject = random.choice(emojis) + " " + subject
    body = template.replace("{{name}}", name)
    body = body.replace("{{sender}}", sender_name)
    body = body.replace("Hi {{name}}", greeting)
    subject = subject.replace("{{name}}", name)
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

def send_whatsapp_pywhatkit(mobile, message):
    """Send WhatsApp via PyWhatKit (100% FREE)"""
    try:
        import pywhatkit
        clean_num = clean_mobile(mobile)
        pywhatkit.sendwhatmsg_instantly(f"+{clean_num}", message, tab_close=True)
        time.sleep(2)
        return True, "✅ WhatsApp sent!"
    except ImportError:
        return False, "❌ PyWhatKit not installed. Run: pip install pywhatkit"
    except Exception as e:
        return False, f"❌ Failed: {str(e)}"

def send_email_smtp(to_email, subject, body, gmail_user, gmail_pass, sender_name):
    """Send email via Gmail SMTP (100% FREE)"""
    try:
        plain = re.sub(r'<[^>]+>', '', body).strip()
        m = MIMEMultipart("alternative")
        m["From"] = f"{sender_name} <{gmail_user}>"
        m["To"] = to_email
        m["Subject"] = subject
        m.attach(MIMEText(plain, "plain"))
        m.attach(MIMEText(body, "html"))
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, to_email, m.as_string())
        server.quit()
        return True, "✅ Email sent!"
    except Exception as e:
        return False, f"❌ Failed: {str(e)}"

# ─── LOGIN/SIGNUP PAGE ───────────────────────────────
if not st.session_state["logged_in"]:
    st.title("🤖 MarketAI - 100% FREE Auto Sender")
    st.markdown("**Send WhatsApp & Email AUTOMATICALLY**")
    
    tab1, tab2 = st.tabs(["🔓 Login", "📝 Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        st.info("💡 Login with your **Email** address")
        
        login_email = st.text_input("📧 Email Address", placeholder="you@gmail.com", key="login_email")
        login_password = st.text_input("🔐 Password", type="password", key="login_password")
        
        if st.button("Login", use_container_width=True, type="primary"):
            if login_email and login_password:
                success, user_id, msg = login_user(login_email, login_password)
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
                st.error("❌ Please enter email and password")
    
    with tab2:
        st.subheader("Create New Account")
        st.info("📋 Sign up with Mobile Verification (2-Step Process)")
        
        # Step 1: Sign Up Form
        if st.session_state["signup_step"] == 1:
            st.write("**Step 1: Enter Your Details**")
            
            col1, col2 = st.columns(2)
            with col1:
                signup_business = st.text_input("🏢 Business Name *", key="signup_business", placeholder="Your Business Name")
                signup_email = st.text_input("📧 Email Address *", key="signup_email", placeholder="you@gmail.com")
                signup_country = st.selectbox("🌍 Country Code *", list(COUNTRY_CODES.keys()), key="signup_country")
            
            with col2:
                signup_phone = st.text_input("📱 Mobile Number *", key="signup_phone", placeholder="Enter mobile number")
                signup_password = st.text_input("🔐 Password *", type="password", key="signup_password", placeholder="Min 6 characters")
                signup_confirm = st.text_input("🔐 Confirm Password *", type="password", key="signup_confirm", placeholder="Re-enter password")
            
            st.divider()
            st.write("**Gmail Credentials (for auto-login):**")
            
            col1, col2 = st.columns(2)
            with col1:
                signup_gmail = st.text_input("📧 Your Gmail Email *", key="signup_gmail", placeholder="your@gmail.com")
            with col2:
                signup_gmail_pass = st.text_input("🔐 Gmail App Password *", type="password", key="signup_gmail_pass", placeholder="16-char app password")
            
            st.caption("ℹ️ Create App Password: Google Account > Security > App passwords")
            
            if st.button("📱 Send OTP to Mobile", use_container_width=True, type="primary"):
                if not signup_business:
                    st.error("❌ Business name required")
                elif not signup_email:
                    st.error("❌ Email required")
                elif not signup_phone:
                    st.error("❌ Mobile number required")
                elif signup_password != signup_confirm:
                    st.error("❌ Passwords don't match")
                elif len(signup_password) < 6:
                    st.error("❌ Password must be at least 6 characters")
                elif not signup_gmail or not signup_gmail_pass:
                    st.error("❌ Gmail credentials required")
                else:
                    success, msg = signup_user_step1(
                        signup_email, signup_country, signup_phone, signup_password,
                        signup_business, signup_gmail, signup_gmail_pass
                    )
                    if success:
                        st.session_state["signup_step"] = 2
                        st.session_state["signup_phone"] = st.session_state.get("signup_data", {}).get("phone")
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
        
        # Step 2: OTP Verification
        elif st.session_state["signup_step"] == 2:
            st.write("**Step 2: Verify Your Mobile Number**")
            st.warning(f"📱 OTP sent to {st.session_state.get('signup_phone', 'your mobile')}")
            st.info("📲 In production, OTP will be sent via SMS. For now, check above for the demo OTP.")
            
            otp_input = st.text_input("🔐 Enter 6-digit OTP", placeholder="000000", key="otp_input", max_chars=6)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Verify OTP", use_container_width=True, type="primary"):
                    if len(otp_input) != 6 or not otp_input.isdigit():
                        st.error("❌ Please enter valid 6-digit OTP")
                    else:
                        success, msg = verify_otp(st.session_state.get("signup_phone"), otp_input)
                        if success:
                            st.session_state["signup_step"] = 1
                            st.session_state["signup_phone"] = None
                            st.success(msg)
                            st.info("👈 Go to **Login** tab and login with your email and password!")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(msg)
            
            with col2:
                if st.button("← Back to Sign Up", use_container_width=True):
                    st.session_state["signup_step"] = 1
                    st.session_state["signup_phone"] = None
                    st.rerun()
    
    st.divider()
    st.markdown("""
    <div style="text-align:center;color:gray;font-size:11px;">
    🤖 **MarketAI - 100% FREE Auto Message Sender**<br>
    ✅ Sign Up: Country Code + Mobile Verification (OTP)<br>
    ✅ Auto Login: Gmail SMTP + PyWhatKit<br>
    ✅ WhatsApp: PyWhatKit (100% Free)<br>
    ✅ Email: Gmail SMTP (100% Free)<br>
    ✅ WhatsApp Links in Excel + Send One by One<br>
    ⚠️ Always get customer consent before sending
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─── LOGGED IN USER AREA ────────────────────────────
user_data = get_user_data(st.session_state["user_id"])
sender_name = user_data.get("business_name", "Your Business")
user_email = user_data.get("email")
user_phone = user_data.get("phone")
gmail_user = user_data.get("gmail_user")
gmail_pass = user_data.get("gmail_pass")

# Display user info
col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
with col1:
    st.title(f"🤖 {sender_name}")
with col2:
    st.caption(f"📧 {user_email}")
with col3:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["user_id"] = None
        st.session_state["customers"] = []
        st.rerun()

st.caption(f"📱 {user_phone} | Auto-login: ✅ Gmail SMTP | ✅ PyWhatKit")

# ─── SIDEBAR ─────────────────────────────────────────
st.sidebar.title(f"🤖 {sender_name}")
st.sidebar.caption(f"📧 {user_email}\n📱 {user_phone}")
st.sidebar.divider()

st.sidebar.header("📁 Step 1: Upload Excel")
uploaded_file = st.sidebar.file_uploader("Choose file", type=["xlsx", "xls", "csv"])
if uploaded_file:
    st.sidebar.success(f"📄 {uploaded_file.name}")
    if st.sidebar.button("🗑️ Delete File", use_container_width=True):
        st.session_state["customers"] = []
        st.session_state["sent_log"] = []
        st.sidebar.success("✅ Deleted!")
        st.rerun()

st.sidebar.header("🔧 Step 2: Templates")
with st.sidebar.expander("📝 Messages", expanded=True):
    whatsapp_template = st.text_area(
        "WhatsApp:", value="Hi {{name}},\n\nThis is a special offer just for you!\n\nVisit us today and get 20% OFF.",
        height=120, help="Use {{name}} and {{sender}}"
    )
    email_subject = st.text_input("Email Subject:", value="Special Offer, {{name}}!")
    email_body = st.text_area(
        "Email Body (HTML):",
        value="""<h2>Hi {{name}},</h2>
<p>We have an exclusive offer!</p>
<p>Get <strong>20% OFF</strong> on your next purchase.</p>""",
        height=120
    )

st.sidebar.header("⚙️ Step 3: Send Settings")
with st.sidebar.expander("🧠 Sending Behavior", expanded=True):
    human_delay_min = st.slider("Min delay (sec):", 10, 300, 30, 5)
    human_delay_max = st.slider("Max delay (sec):", 30, 600, 120, 10)
    max_per_hour = st.slider("Max per hour:", 5, 50, 20, 5)
    max_per_day = st.slider("Max per day:", 10, 200, 80, 10)
    use_business_hours = st.checkbox("Only 9AM-8PM", True)
    add_variations = st.checkbox("Random variations ✅", True)

st.sidebar.header("✅ Auto-Login Status")
with st.sidebar.expander("Connection Status", expanded=True):
    st.success("✅ Gmail SMTP - Ready to send emails")
    st.success("✅ PyWhatKit - Ready to send WhatsApp")
    st.info("Both services are automatically configured with your Gmail credentials.")

# ─── MAIN AREA ──────────────────────────────────────
st.markdown("""
**Send WhatsApp & Email AUTOMATICALLY - 100% FREE**
- ✅ WhatsApp: PyWhatKit (auto-configured)
- ✅ Email: Gmail SMTP (auto-configured)
- ✅ Generate WhatsApp Links in Excel
- ✅ Send messages one by one with delays
- ✅ Customers see your business name
""")

# Upload
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        is_valid, msg, mapping = validate_excel(df)
        if is_valid:
            st.success(msg)
            with st.expander("📊 Preview", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)
                st.caption(f"Total: {len(df)} rows")
            if st.button("📥 Load Customers", use_container_width=True):
                st.session_state["customers"] = save_customers(df, mapping)
                st.session_state["sent_log"] = []
                st.session_state["sending_active"] = False
                st.success(f"Loaded {len(st.session_state['customers'])} customers!")
                st.rerun()
        else:
            st.error(msg)
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("👈 Upload Excel from sidebar")
    with st.expander("📋 Required Columns"):
        st.dataframe(pd.DataFrame({
            "Customer Name": ["Rahul S.", "Priya M."],
            "Mobile": ["9876543210", "9123456789"],
            "Email": ["rahul@email.com", "priya@email.com"]
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
    c5.metric("📊 /hr", f"{last_hour}/{max_per_hour}")

    if last_hour >= max_per_hour:
        st.warning(f"⚠️ Hourly limit hit!")
    if today >= max_per_day:
        st.error(f"🚫 Daily limit reached")
    if use_business_hours and not is_business_hours():
        st.warning(f"🌙 Outside business hours")

    # ─── SENDING CONTROLS ────────────────────────────
    st.subheader("🎯 Send Messages One by One")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if not st.session_state["sending_active"]:
            if st.button("▶️ START AUTO SENDING", use_container_width=True, type="primary"):
                if last_hour >= max_per_hour:
                    st.error("Hourly limit reached!")
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
        if st.button("🔗 Generate WhatsApp Links", use_container_width=True):
            for c in customers:
                if c["mobile"] and not c["whatsapp_sent"]:
                    msg = randomize_message(whatsapp_template, c["name"], sender_name) if add_variations else whatsapp_template.replace("{{name}}", c["name"])
                    c["whatsapp_link"] = generate_whatsapp_link(c["mobile"], msg)
            st.success("✅ WhatsApp links generated for all customers!")
            st.rerun()

    with col_c:
        if st.button("📥 Export Report", use_container_width=True):
            rows = [{
                "Name": c["name"], "Mobile": c["mobile"], "Email": c["email"],
                "WhatsApp Link": c.get("whatsapp_link", ""),
                "WhatsApp": "✅" if c["whatsapp_sent"] else "❌",
                "Email": "✅" if c["email_sent"] else "❌",
                "Sent": str(c.get("sent_at", ""))
            } for c in customers]
            df_export = pd.DataFrame(rows)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv = df_export.to_csv(index=False)
            st.download_button("📥 Download CSV", data=csv, file_name=f"report_{ts}.csv", mime="text/csv")

    # ─── AUTO SENDING LOOP ────────────────────────────
    if st.session_state["sending_active"]:
        lh, td = get_batch_stats(customers)
        if lh >= max_per_hour or td >= max_per_day or (use_business_hours and not is_business_hours()):
            st.session_state["sending_active"] = False
            st.rerun()

        # Find next customer
        next_c = None
        for c in customers:
            if not c["whatsapp_sent"] and c["mobile"]:
                next_c = c
                break
        if next_c is None:
            for c in customers:
                if not c["email_sent"] and c["email"]:
                    next_c = c
                    break

        if next_c is None:
            st.success("✅ All messages sent!")
            st.session_state["sending_active"] = False
            st.rerun()

        c = next_c
        with st.container(border=True):
            st.info(f"📤 Sending to: **{c['name']}** from **{sender_name}**")

            # WhatsApp
            if c["mobile"] and not c["whatsapp_sent"]:
                with st.spinner(f"💬 Sending WhatsApp to {c['name']}... (Browser will open)"):
                    msg = randomize_message(whatsapp_template, c["name"], sender_name) if add_variations else whatsapp_template.replace("{{name}}", c["name"])
                    
                    success, response = send_whatsapp_pywhatkit(c["mobile"], msg)
                    
                    delay = get_human_delay()
                    prog = st.progress(0)
                    for i in range(100):
                        time.sleep(delay / 100)
                        prog.progress(i + 1)
                    
                    if success:
                        c["whatsapp_sent"] = True
                        c["sent_at"] = datetime.now()
                        c["whatsapp_link"] = generate_whatsapp_link(c["mobile"], msg)
                        st.success(f"✅ {response}")
                        st.session_state["sent_log"].append({
                            "name": c["name"], "type": "WhatsApp",
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "status": "✅ Sent"
                        })
                    else:
                        st.error(f"❌ {response}")
                        st.session_state["sent_log"].append({
                            "name": c["name"], "type": "WhatsApp",
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "status": "❌ Failed"
                        })

            # Email
            elif c["email"] and not c["email_sent"]:
                with st.spinner(f"📧 Sending email to {c['name']}..."):
                    subj, body = randomize_email(email_body, c["name"], email_subject, sender_name) if add_variations else (
                        email_subject.replace("{{name}}", c["name"]),
                        email_body.replace("{{name}}", c["name"])
                    )
                    
                    success, response = send_email_smtp(c["email"], subj, body, gmail_user, gmail_pass, sender_name)
                    
                    delay = get_human_delay()
                    prog = st.progress(0)
                    for i in range(100):
                        time.sleep(delay / 100)
                        prog.progress(i + 1)
                    
                    if success:
                        c["email_sent"] = True
                        c["sent_at"] = datetime.now()
                        st.success(f"✅ {response}")
                        st.session_state["sent_log"].append({
                            "name": c["name"], "type": "Email",
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "status": "✅ Sent"
                        })
                    else:
                        st.error(f"❌ {response}")
                        st.session_state["sent_log"].append({
                            "name": c["name"], "type": "Email",
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "status": "❌ Failed"
                        })

        st.rerun()

    # ─── CUSTOMER TABLE ──────────────────────────
    st.subheader("👥 Customers with WhatsApp Links")
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
            if c.get("whatsapp_link"):
                st.markdown(f'<a href="{c["whatsapp_link"]}" target="_blank"><button style="background:#25D366;color:white;border:none;padding:5px 10px;border-radius:5px;font-size:12px;">💬 Link</button></a>', unsafe_allow_html=True)
        with cols[4]:
            if c.get("sent_at"):
                st.caption(c["sent_at"].strftime("%H:%M") if isinstance(c["sent_at"], datetime) else c["sent_at"])

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
<div style="text-align:center;padding:20px;color:gray;font-size:11px;">
🤖 **MarketAI - 100% FREE Auto Message Sender**<br>
✅ Sign Up: Country Code + Mobile Verification (OTP)<br>
✅ Auto Login: Gmail SMTP + PyWhatKit (Fully Automated)<br>
💬 WhatsApp: PyWhatKit (100% Free) + Links in Excel<br>
📧 Email: Gmail SMTP (100% Free)<br>
✅ Send messages one by one with human-like delays<br>
⚠️ Always get customer consent before sending
</div>
""", unsafe_allow_html=True)
