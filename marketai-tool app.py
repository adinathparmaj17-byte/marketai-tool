# ============================================================
# MarketAI - 100% FREE WhatsApp & Email Marketing Tool
# CLOUD VERSION (Supabase Integrated)
# ============================================================

import pandas as pd
import streamlit as st
import time
import re
import os
import random
import json
import smtplib
import string
import urllib.parse
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client

# ─── Page Config ────────────────────────────────────
st.set_page_config(page_title="MarketAI - 100% FREE Sender", page_icon="🤖", layout="wide")

# ─── SUPABASE CLOUD DATABASE CONNECTION ─────────────
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase: Client = init_connection()
except Exception as e:
    st.error("⚠️ Could not connect to Supabase. Check your .streamlit/secrets.toml file!")
    st.stop()

# ─── OTP & VERIFICATION (Local for MVP) ─────────────
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

# ─── DATABASE FUNCTIONS ──────────────────────────────
COUNTRY_CODES = {
    "🇮🇳 India": "+91", "🇵🇰 Pakistan": "+92", "🇧🇩 Bangladesh": "+880",
    "🇬🇧 UK": "+44", "🇺🇸 USA": "+1", "🇨🇦 Canada": "+1",
    "🇦🇺 Australia": "+61", "🇳🇿 New Zealand": "+64", "🇿🇦 South Africa": "+27",
    "🇩🇪 Germany": "+49", "🇫🇷 France": "+33", "🇮🇹 Italy": "+39",
    "🇪🇸 Spain": "+34", "🇸🇬 Singapore": "+65", "🇲🇾 Malaysia": "+60",
}

def validate_phone_with_country(country, phone):
    phone = re.sub(r'[\s\-\+\(\)]', '', str(phone))
    country_code = COUNTRY_CODES.get(country, "").replace("+", "")
    if not country_code: return None, "Invalid country"
    if len(phone) < 8: return None, "Phone number too short"
    if phone.startswith(country_code): phone = phone[len(country_code):]
    return f"+{country_code}{phone}", "Valid"

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def find_user_by_email(email):
    """Find user data by email in Supabase"""
    response = supabase.table("users").select("*").eq("email", email).execute()
    if len(response.data) > 0:
        return response.data[0]
    return None

def find_user_by_phone(phone):
    """Find user data by phone in Supabase"""
    response = supabase.table("users").select("*").eq("phone", phone).execute()
    if len(response.data) > 0:
        user = response.data[0]
        return user["email"], user
    return None, None

def save_new_user(user_data):
    """Insert a new user into Supabase"""
    try:
        supabase.table("users").insert(user_data).execute()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

def reset_password(email, new_password):
    """Reset user password in Supabase"""
    try:
        supabase.table("users").update({"password": new_password}).eq("email", email).execute()
        return True
    except Exception as e:
        print(f"Password reset error: {e}")
        return False

# ─── AUTHENTICATION LOGIC ────────────────────────────
def signup_user_step1(email, country, phone, password, business_name, gmail_user, gmail_pass):
    if not business_name or len(business_name.strip()) < 2:
        return False, "❌ Business name must be at least 2 characters"
    if not validate_email(email):
        return False, "❌ Invalid email format"
        
    if find_user_by_email(email):
        return False, "❌ Email already registered"
        
    full_phone, phone_msg = validate_phone_with_country(country, phone)
    if not full_phone:
        return False, f"❌ {phone_msg}"
        
    _, existing_phone = find_user_by_phone(full_phone)
    if existing_phone:
        return False, "❌ Phone number already registered"
        
    if not password or len(password) < 6:
        return False, "❌ Password must be at least 6 characters"
    if not gmail_user or not gmail_pass:
        return False, "❌ Please enter Gmail credentials"
        
    otp = generate_otp()
    if not save_otp_verification(full_phone, otp):
        return False, "❌ Error generating OTP. Please try again."
        
    st.session_state["signup_data"] = {
        "email": email, "country": country, "phone": full_phone,
        "password": password, "business_name": business_name.strip(),
        "gmail_user": gmail_user, "gmail_pass": gmail_pass,
    }
    return True, f"✅ OTP sent to {full_phone}\n\n📲 **Your OTP is: {otp}**"

def verify_otp(phone, otp_input):
    signup_data = st.session_state.get("signup_data", {})
    saved_otp, otp_expiry = load_otp_verification(phone)
    
    if not saved_otp or str(otp_input).strip() != str(saved_otp).strip():
        return False, "❌ Invalid OTP"
        
    user_data = {
        "email": signup_data.get("email"),
        "password": signup_data.get("password"),
        "business_name": signup_data.get("business_name"),
        "country": signup_data.get("country"),
        "phone": phone,
        "gmail_user": signup_data.get("gmail_user"),
        "gmail_pass": signup_data.get("gmail_pass")
    }
    
    if save_new_user(user_data):
        if os.path.exists("otp_data.json"):
            os.remove("otp_data.json")
        return True, "✅ Mobile verified! Account created successfully!"
    else:
        return False, "❌ Database Error: Could not create account."

def login_user(email, password):
    if not email or not password:
        return False, None, "❌ Please enter email and password"
    if not validate_email(email):
        return False, None, "❌ Invalid email format"
        
    user_data = find_user_by_email(email)
    
    if user_data and user_data["password"] == password:
        return True, email, f"✅ Welcome {user_data['business_name']}!"
    else:
        return False, None, "❌ Invalid email or password"

def get_user_data(email):
    return find_user_by_email(email) or {}

# ─── SESSION State ──────────────────────────────────
for v in ["logged_in", "user_id", "customers", "sent_log", "sending_active", "signup_step", "signup_phone", "signup_data", "forgot_step", "forgot_phone", "forgot_user_id"]:
    if v not in st.session_state:
        if v == "customers": st.session_state[v] = []
        elif v == "sent_log": st.session_state[v] = []
        elif v == "signup_step": st.session_state[v] = 1
        elif v == "forgot_step": st.session_state[v] = 1
        else: st.session_state[v] = None if v != "sending_active" else False

# ─── CONFIG & HELPERS ───────────────────────────────
HUMAN_DELAY_MIN = 30
HUMAN_DELAY_MAX = 120
BUSINESS_HOURS_START = 9
BUSINESS_HOURS_END = 20
GREETINGS = ["Hi {name}!", "Hello {name},", "Hey {name}!", "Hi there {name}!", "Hello {name} 👋", "Hey {name} 🙌"]

def validate_excel(df):
    df.columns = [str(c).strip().lower() for c in df.columns]
    mapping = {}
    for col in df.columns:
        if "name" in col or "customer" in col: mapping[col] = "name"
        elif any(x in col for x in ["mobile", "phone", "contact", "whatsapp", "number"]): mapping[col] = "mobile"
        elif "email" in col: mapping[col] = "email"
    if "name" not in mapping.values(): return False, "No 'Name' column found", mapping
    if "mobile" not in mapping.values() and "email" not in mapping.values(): return False, "Need 'Mobile' or 'Email' column", mapping
    return True, "Excel looks good!", mapping

def clean_mobile(num):
    num = re.sub(r'[\s\-\+\(\)]', '', str(num))
    if num.startswith("91") and len(num) == 12: return num
    elif num.startswith("0") and len(num) == 11: return "91" + num[1:]
    elif len(num) == 10: return "91" + num
    return num

def generate_whatsapp_link(mobile, message):
    clean_num = clean_mobile(mobile)
    return f"https://wa.me/{clean_num}?text={urllib.parse.quote(message)}"

def save_customers(df, mapping):
    customers = []
    for idx, row in df.iterrows():
        nc = [k for k, v in mapping.items() if v == "name"][0]
        name = str(row[nc]).strip()
        mobile = str(row[[k for k, v in mapping.items() if v == "mobile"][0]]).strip() if "mobile" in mapping.values() else ""
        email = str(row[[k for k, v in mapping.items() if v == "email"][0]]).strip() if "email" in mapping.values() else ""
        if name.lower() in ["nan", "nat", "", "none"]: name = f"Customer {idx+1}"
        customers.append({
            "id": idx, "name": name, 
            "mobile": mobile if mobile.lower() not in ["nan","nat","","none"] else "",
            "email": email if email.lower() not in ["nan","nat","","none"] else "",
            "whatsapp_sent": False, "email_sent": False, "whatsapp_link": "", "sent_at": None
        })
    return customers

def randomize_message(template, name, sender_name):
    greeting = random.choice(GREETINGS).format(name=name)
    msg = template.replace("{{name}}", name).replace("{{sender}}", sender_name)
    if msg.startswith("Hi") or msg.startswith("Hello") or msg.startswith("Hey"):
        lines = msg.split("\n", 1)
        if len(lines) > 1: msg = greeting + "\n" + lines[1]
    msg = msg.strip() + f"\n\n— {sender_name}"
    if random.random() > 0.4: msg += " " + random.choice(["🎉", "🔥", "💥", "✨", "🎊", "🚀", "💪", "👋", "⭐", "🎯"])
    return msg

def randomize_email(template, name, subject, sender_name):
    greeting = random.choice(GREETINGS).format(name=name)
    if random.random() > 0.5: subject = random.choice(["🎉", "🔥", "✨", "🚀", "💌", "📢"]) + " " + subject
    body = template.replace("{{name}}", name).replace("{{sender}}", sender_name).replace("Hi {{name}}", greeting)
    subject = subject.replace("{{name}}", name)
    body += f"\n\n<p><strong>Sent by: {sender_name}</strong></p>"
    return subject, body

def get_batch_stats(customers):
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sent_hr = sum(1 for c in customers if c.get("sent_at") and c["sent_at"] > one_hour_ago)
    sent_day = sum(1 for c in customers if c.get("sent_at") and c["sent_at"] > today_start)
    return sent_hr, sent_day

def send_whatsapp_pywhatkit(mobile, message):
    try:
        import pywhatkit
        clean_num = clean_mobile(mobile)
        pywhatkit.sendwhatmsg_instantly(f"+{clean_num}", message, tab_close=True)
        time.sleep(2)
        return True, "✅ WhatsApp sent!"
    except ImportError: return False, "❌ PyWhatKit not installed."
    except Exception as e: return False, f"❌ Failed: {str(e)}"

def send_email_smtp(to_email, subject, body, gmail_user, gmail_pass, sender_name):
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
    except Exception as e: return False, f"❌ Failed: {str(e)}"

# ============================================================
# LOGIN / SIGNUP / FORGOT PASSWORD PAGE
# ============================================================
if not st.session_state["logged_in"]:
    st.title("🤖 MarketAI - Cloud Auto Sender")
    st.markdown("**Send WhatsApp & Email AUTOMATICALLY**")

    tab1, tab2, tab3 = st.tabs(["🔓 Login", "📝 Sign Up", "🔑 Forgot Password"])

    with tab1:
        st.subheader("Login to Your Account")
        login_email = st.text_input("📧 Email Address", placeholder="you@gmail.com", key="login_email")
        login_password = st.text_input("🔐 Password", type="password", key="login_password")
        if st.button("Login", use_container_width=True, type="primary"):
            success, user_id, msg = login_user(login_email, login_password)
            if success:
                st.session_state["logged_in"] = True
                st.session_state["user_id"] = user_id
                st.success(msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)

    with tab2:
        st.subheader("Create New Account")
        if st.session_state["signup_step"] == 1:
            col1, col2 = st.columns(2)
            with col1:
                signup_business = st.text_input("🏢 Business Name *", key="signup_business")
                signup_email = st.text_input("📧 Email Address *", key="signup_email")
                signup_country = st.selectbox("🌍 Country Code *", list(COUNTRY_CODES.keys()), key="signup_country")
            with col2:
                signup_phone = st.text_input("📱 Mobile Number *", key="signup_phone")
                signup_password = st.text_input("🔐 Password *", type="password", key="signup_password")
                signup_confirm = st.text_input("🔐 Confirm Password *", type="password", key="signup_confirm")
            
            st.divider()
            st.write("**Gmail Credentials (for auto-login):**")
            col1, col2 = st.columns(2)
            with col1: signup_gmail = st.text_input("📧 Your Gmail Email *", key="signup_gmail")
            with col2: signup_gmail_pass = st.text_input("🔐 Gmail App Password *", type="password", key="signup_gmail_pass")
            
            if st.button("📱 Send OTP to Mobile", use_container_width=True, type="primary"):
                if signup_password != signup_confirm:
                    st.error("❌ Passwords don't match")
                else:
                    success, msg = signup_user_step1(signup_email, signup_country, signup_phone, signup_password, signup_business, signup_gmail, signup_gmail_pass)
                    if success:
                        st.session_state["signup_step"] = 2
                        st.session_state["signup_phone"] = st.session_state.get("signup_data", {}).get("phone")
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else: st.error(msg)

        elif st.session_state["signup_step"] == 2:
            st.warning(f"📱 OTP sent to {st.session_state.get('signup_phone')}")
            otp_input = st.text_input("🔐 Enter 6-digit OTP", key="otp_input_signup", max_chars=6)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Verify OTP", use_container_width=True, type="primary"):
                    success, msg = verify_otp(st.session_state.get("signup_phone"), otp_input)
                    if success:
                        st.session_state["signup_step"] = 1
                        st.session_state["signup_phone"] = None
                        st.success(msg)
                        time.sleep(2)
                        st.rerun()
                    else: st.error(msg)
            with col2:
                if st.button("← Back", use_container_width=True):
                    st.session_state["signup_step"] = 1
                    st.rerun()

    with tab3:
        st.subheader("🔑 Forgot Password")
        forgot_step = st.session_state.get("forgot_step", 1)
        if forgot_step == 1:
            forgot_method = st.radio("Find account by:", ["📧 Email", "📱 Phone Number"], key="forgot_method")
            if forgot_method == "📧 Email":
                forgot_email = st.text_input("📧 Enter registered email", key="forgot_email")
                if st.button("🔍 Find Account", use_container_width=True):
                    user_data = find_user_by_email(forgot_email)
                    if user_data:
                        st.session_state["forgot_user_id"] = forgot_email
                        st.session_state["forgot_phone"] = user_data.get("phone")
                        st.session_state["forgot_step"] = 2
                        st.rerun()
                    else: st.error("❌ Account not found")
            else:
                forgot_country = st.selectbox("🌍 Country Code", list(COUNTRY_CODES.keys()), key="forgot_country")
                forgot_phone_input = st.text_input("📱 Enter mobile", key="forgot_phone_input")
                if st.button("🔍 Find Account", use_container_width=True):
                    full_phone, _ = validate_phone_with_country(forgot_country, forgot_phone_input)
                    email_id, user_data = find_user_by_phone(full_phone)
                    if user_data:
                        st.session_state["forgot_user_id"] = email_id
                        st.session_state["forgot_phone"] = full_phone
                        st.session_state["forgot_step"] = 2
                        st.rerun()
                    else: st.error("❌ Account not found")

        elif forgot_step == 2:
            forgot_phone_display = st.session_state.get("forgot_phone")
            if not st.session_state.get("forgot_otp_sent"):
                if st.button("📱 Send OTP", use_container_width=True, type="primary"):
                    otp = generate_otp()
                    save_otp_verification(forgot_phone_display, otp)
                    st.session_state["forgot_otp_sent"] = True
                    st.success(f"✅ OTP sent! 📲 **Your OTP is: {otp}**")
                    st.rerun()
            else:
                forgot_otp_input = st.text_input("🔐 Enter OTP", key="forgot_otp_input", max_chars=6)
                if st.button("✅ Verify", use_container_width=True, type="primary"):
                    saved_otp, _ = load_otp_verification(forgot_phone_display)
                    if str(forgot_otp_input).strip() == str(saved_otp).strip():
                        st.session_state["forgot_step"] = 3
                        st.rerun()
                    else: st.error("❌ Invalid OTP")

        elif forgot_step == 3:
            new_pass = st.text_input("🔐 New Password", type="password", key="new_pass")
            confirm_pass = st.text_input("🔐 Confirm Password", type="password", key="confirm_pass")
            if st.button("✅ Reset Password", use_container_width=True, type="primary"):
                if new_pass == confirm_pass and reset_password(st.session_state.get("forgot_user_id"), new_pass):
                    st.session_state["forgot_step"] = 1
                    st.success("✅ Password reset!")
                    time.sleep(2)
                    st.rerun()
                else: st.error("❌ Error resetting password")
    st.stop()

# ============================================================
# LOGGED IN USER AREA
# ============================================================
user_data = get_user_data(st.session_state["user_id"])
sender_name = user_data.get("business_name", "Your Business")
user_email = user_data.get("email")
user_phone = user_data.get("phone")
gmail_user = user_data.get("gmail_user")
gmail_pass = user_data.get("gmail_pass")

col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
with col1: st.title(f"🤖 {sender_name}")
with col3:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()

st.sidebar.header("📁 Step 1: Upload Excel")
uploaded_file = st.sidebar.file_uploader("Choose file", type=["xlsx", "xls", "csv"])
if st.sidebar.button("🗑️ Clear Data", use_container_width=True):
    st.session_state["customers"] = []
    st.rerun()

st.sidebar.header("🔧 Step 2: Templates")
whatsapp_template = st.sidebar.text_area("WhatsApp:", "Hi {{name}},\n\nSpecial offer!")
email_subject = st.sidebar.text_input("Email Subject:", "Special Offer, {{name}}!")
email_body = st.sidebar.text_area("Email HTML:", "<h2>Hi {{name}},</h2>")

st.sidebar.header("⚙️ Step 3: Settings")
max_per_hour = st.sidebar.slider("Max per hour:", 5, 50, 20)
max_per_day = st.sidebar.slider("Max per day:", 10, 200, 80)
add_variations = st.sidebar.checkbox("Random variations ✅", True)

if uploaded_file is not None and not st.session_state["customers"]:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
    is_valid, msg, mapping = validate_excel(df)
    if is_valid and st.button("📥 Load Customers", use_container_width=True):
        st.session_state["customers"] = save_customers(df, mapping)
        st.rerun()

if st.session_state["customers"]:
    customers = st.session_state["customers"]
    last_hour, today = get_batch_stats(customers)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Total", len(customers))
    c2.metric("⏳ Remaining", len([c for c in customers if not c['whatsapp_sent']]))
    c3.metric("📊 Sent /hr", f"{last_hour}/{max_per_hour}")

    if not st.session_state["sending_active"]:
        if st.button("▶️ START AUTO SENDING", use_container_width=True, type="primary"):
            st.session_state["sending_active"] = True
            st.rerun()
    else:
        if st.button("⏹️ STOP", use_container_width=True, type="secondary"):
            st.session_state["sending_active"] = False
            st.rerun()

    # The Sending Loop
    if st.session_state["sending_active"]:
        if last_hour >= max_per_hour or today >= max_per_day:
            st.session_state["sending_active"] = False
            st.rerun()
            
        next_c = next((c for c in customers if not c["whatsapp_sent"] and c["mobile"]), None)
        if not next_c: next_c = next((c for c in customers if not c["email_sent"] and c["email"]), None)
        
        if next_c:
            st.info(f"📤 Sending to: **{next_c['name']}**")
            if next_c["mobile"] and not next_c["whatsapp_sent"]:
                msg = randomize_message(whatsapp_template, next_c["name"], sender_name) if add_variations else whatsapp_template
                success, response = send_whatsapp_pywhatkit(next_c["mobile"], msg)
                if success:
                    next_c["whatsapp_sent"] = True
                    next_c["sent_at"] = datetime.now()
            elif next_c["email"] and not next_c["email_sent"]:
                subj, body = randomize_email(email_body, next_c["name"], email_subject, sender_name) if add_variations else (email_subject, email_body)
                success, response = send_email_smtp(next_c["email"], subj, body, gmail_user, gmail_pass, sender_name)
                if success:
                    next_c["email_sent"] = True
                    next_c["sent_at"] = datetime.now()
            
            time.sleep(random.randint(HUMAN_DELAY_MIN, HUMAN_DELAY_MAX))
            st.rerun()
        else:
            st.session_state["sending_active"] = False
            st.success("✅ All messages sent!")
            st.rerun()
