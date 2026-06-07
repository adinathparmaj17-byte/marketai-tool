# ============================================================
# MarketAI - 100% FREE WhatsApp & Email Marketing Tool
# CLOUD VERSION (Supabase Integrated) + Smart Excel Reader
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
import hashlib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client

# ─── Page Config ────────────────────────────────────
st.set_page_config(
    page_title="MarketAI - FREE Sender",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ─────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 10px;
        border-radius: 8px;
        color: #155724;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        padding: 10px;
        border-radius: 8px;
        color: #856404;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
    .sidebar .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ─── SUPABASE CONNECTION ─────────────────────────────
@st.cache_resource
def init_connection():
    """Initialize Supabase connection with error handling"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except KeyError as e:
        st.error(f"⚠️ Missing secret: {e}. Check .streamlit/secrets.toml")
        return None
    except Exception as e:
        st.error(f"⚠️ Supabase connection failed: {e}")
        return None

supabase = init_connection()
if not supabase:
    st.stop()

# ─── SECURITY HELPERS ────────────────────────────────
def hash_password(password: str) -> str:
    """Hash password using SHA-256 (use bcrypt in production)"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_otp() -> str:
    """Generate secure 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

# ─── CONSTANTS ───────────────────────────────────────
COUNTRY_CODES = {
    "🇮🇳 India (+91)": "+91",
    "🇵🇰 Pakistan (+92)": "+92",
    "🇧🇩 Bangladesh (+880)": "+880",
    "🇬🇧 UK (+44)": "+44",
    "🇺🇸 USA (+1)": "+1",
    "🇨🇦 Canada (+1)": "+1",
    "🇦🇺 Australia (+61)": "+61",
    "🇳🇿 New Zealand (+64)": "+64",
    "🇿🇦 South Africa (+27)": "+27",
    "🇩🇪 Germany (+49)": "+49",
    "🇫🇷 France (+33)": "+33",
    "🇮🇹 Italy (+39)": "+39",
    "🇪🇸 Spain (+34)": "+34",
    "🇸🇬 Singapore (+65)": "+65",
    "🇲🇾 Malaysia (+60)": "+60",
    "🇦🇪 UAE (+971)": "+971",
    "🇸🇦 Saudi Arabia (+966)": "+966",
    "🇳🇬 Nigeria (+234)": "+234",
    "🇰🇪 Kenya (+254)": "+254",
    "🇧🇷 Brazil (+55)": "+55",
}

HUMAN_DELAY_MIN = 30
HUMAN_DELAY_MAX = 120

GREETINGS = [
    "Hi {name}!",
    "Hello {name},",
    "Hey {name}!",
    "Hi there {name}!",
    "Hello {name} 👋",
    "Hey {name} 🙌",
    "Dear {name},",
    "Good day {name}!",
]

EMOJIS = ["🎉", "🔥", "💥", "✨", "🎊", "🚀", "💪", "👋", "⭐", "🎯", "💎", "🎁"]

# ─── OTP MANAGEMENT (Supabase-based) ─────────────────
def save_otp_supabase(phone: str, otp: str) -> bool:
    """Save OTP to Supabase for better cloud compatibility"""
    try:
        expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
        # Upsert OTP record
        supabase.table("otp_verifications").upsert({
            "phone": phone,
            "otp": otp,
            "expiry": expiry,
            "created_at": datetime.now().isoformat()
        }, on_conflict="phone").execute()
        return True
    except Exception:
        # Fallback to session state if table doesn't exist
        if "otp_store" not in st.session_state:
            st.session_state["otp_store"] = {}
        st.session_state["otp_store"][phone] = {
            "otp": otp,
            "expiry": (datetime.now() + timedelta(minutes=10)).isoformat()
        }
        return True

def verify_otp_supabase(phone: str, otp_input: str) -> tuple[bool, str]:
    """Verify OTP from Supabase or session fallback"""
    try:
        # Try Supabase first
        response = supabase.table("otp_verifications").select("*").eq("phone", phone).execute()
        if response.data:
            record = response.data[0]
            if str(otp_input).strip() != str(record["otp"]).strip():
                return False, "❌ Invalid OTP. Please check and try again."
            expiry = datetime.fromisoformat(record["expiry"])
            if datetime.now() > expiry:
                return False, "❌ OTP expired. Please request a new one."
            # Delete used OTP
            supabase.table("otp_verifications").delete().eq("phone", phone).execute()
            return True, "✅ OTP verified!"
    except Exception:
        pass

    # Fallback to session state
    otp_store = st.session_state.get("otp_store", {})
    if phone not in otp_store:
        return False, "❌ OTP not found. Please request a new one."

    record = otp_store[phone]
    if str(otp_input).strip() != str(record["otp"]).strip():
        return False, "❌ Invalid OTP."

    expiry = datetime.fromisoformat(record["expiry"])
    if datetime.now() > expiry:
        return False, "❌ OTP expired."

    del st.session_state["otp_store"][phone]
    return True, "✅ OTP verified!"

# ─── DATABASE FUNCTIONS ──────────────────────────────
def validate_phone(country: str, phone: str) -> tuple[str | None, str]:
    """Validate and format phone number"""
    phone_clean = re.sub(r'[\s\-\+\(\)]', '', str(phone))
    country_code = COUNTRY_CODES.get(country, "").replace("+", "")

    if not country_code:
        return None, "Invalid country selected"
    if len(phone_clean) < 7:
        return None, "Phone number too short"
    if len(phone_clean) > 15:
        return None, "Phone number too long"
    if not phone_clean.isdigit():
        return None, "Phone must contain only digits"

    # Remove country code if already present
    if phone_clean.startswith(country_code):
        phone_clean = phone_clean[len(country_code):]

    return f"+{country_code}{phone_clean}", "Valid"

def validate_email_format(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

@st.cache_data(ttl=60)
def find_user_by_email(email: str) -> dict | None:
    """Find user by email with caching"""
    try:
        response = supabase.table("users").select("*").eq("email", email.lower()).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

def find_user_by_phone(phone: str) -> tuple[str | None, dict | None]:
    """Find user by phone number"""
    try:
        response = supabase.table("users").select("*").eq("phone", phone).execute()
        if response.data:
            user = response.data[0]
            return user["email"], user
        return None, None
    except Exception as e:
        st.error(f"Database error: {e}")
        return None, None

def save_new_user(user_data: dict) -> tuple[bool, str]:
    """Insert new user into Supabase"""
    try:
        # Hash password before saving
        user_data["password"] = hash_password(user_data["password"])
        supabase.table("users").insert(user_data).execute()
        # Clear cache
        find_user_by_email.clear()
        return True, "✅ Account created successfully!"
    except Exception as e:
        error_msg = str(e)
        if "duplicate" in error_msg.lower():
            return False, "❌ Email or phone already registered."
        return False, f"❌ Database error: {error_msg}"

def update_password(email: str, new_password: str) -> tuple[bool, str]:
    """Update user password"""
    try:
        hashed = hash_password(new_password)
        supabase.table("users").update({"password": hashed}).eq("email", email).execute()
        find_user_by_email.clear()
        return True, "✅ Password updated successfully!"
    except Exception as e:
        return False, f"❌ Error: {e}"

# ─── AUTHENTICATION ───────────────────────────────────
def signup_step1(
    email: str, country: str, phone: str,
    password: str, confirm: str,
    business_name: str, gmail_user: str, gmail_pass: str
) -> tuple[bool, str]:
    """Validate signup form and send OTP"""

    # Validations
    if not business_name or len(business_name.strip()) < 2:
        return False, "❌ Business name must be at least 2 characters."
    if not email or not validate_email_format(email):
        return False, "❌ Invalid email format."
    if find_user_by_email(email):
        return False, "❌ This email is already registered."

    full_phone, phone_msg = validate_phone(country, phone)
    if not full_phone:
        return False, f"❌ Phone error: {phone_msg}"

    _, existing = find_user_by_phone(full_phone)
    if existing:
        return False, "❌ This phone number is already registered."

    if not password or len(password) < 6:
        return False, "❌ Password must be at least 6 characters."
    if password != confirm:
        return False, "❌ Passwords do not match."
    if not gmail_user or not validate_email_format(gmail_user):
        return False, "❌ Invalid Gmail address."
    if not gmail_pass or len(gmail_pass) < 8:
        return False, "❌ Gmail App Password must be at least 8 characters."

    # Generate & save OTP
    otp = generate_otp()
    save_otp_supabase(full_phone, otp)

    # Store pending signup data in session
    st.session_state["pending_signup"] = {
        "email": email.lower().strip(),
        "country": country,
        "phone": full_phone,
        "password": password,
        "business_name": business_name.strip(),
        "gmail_user": gmail_user.strip(),
        "gmail_pass": gmail_pass,
    }

    # In production: Send OTP via SMS API (Twilio, MSG91, etc.)
    # For MVP: Display OTP directly
    return True, f"📲 **OTP for {full_phone}: `{otp}`**\n\n_In production, this would be sent via SMS._"

def complete_signup(otp_input: str) -> tuple[bool, str]:
    """Complete signup after OTP verification"""
    pending = st.session_state.get("pending_signup", {})
    if not pending:
        return False, "❌ Session expired. Please start over."

    phone = pending.get("phone")
    verified, msg = verify_otp_supabase(phone, otp_input)

    if not verified:
        return False, msg

    user_data = {
        "email": pending["email"],
        "password": pending["password"],  # Will be hashed in save_new_user
        "business_name": pending["business_name"],
        "country": pending["country"],
        "phone": pending["phone"],
        "gmail_user": pending["gmail_user"],
        "gmail_pass": pending["gmail_pass"],
        "created_at": datetime.now().isoformat()
    }

    success, message = save_new_user(user_data)
    if success:
        st.session_state.pop("pending_signup", None)

    return success, message

def login_user(email: str, password: str) -> tuple[bool, str | None, str]:
    """Authenticate user login"""
    if not email or not password:
        return False, None, "❌ Please enter both email and password."
    if not validate_email_format(email):
        return False, None, "❌ Invalid email format."

    user = find_user_by_email(email.lower().strip())

    if user and user["password"] == hash_password(password):
        return True, user["email"], f"✅ Welcome back, **{user['business_name']}**!"

    return False, None, "❌ Invalid email or password."

# ─── SESSION STATE INITIALIZATION ────────────────────
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "logged_in": False,
        "user_id": None,
        "customers": [],
        "sent_log": [],
        "sending_active": False,
        "signup_step": 1,
        "forgot_step": 1,
        "forgot_user_email": None,
        "forgot_phone": None,
        "forgot_otp_sent": False,
        "pending_signup": {},
        "otp_store": {},
        "send_mode": "whatsapp",
        "current_send_index": 0,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()

# ─── EXCEL PROCESSING ────────────────────────────────
def detect_columns(df: pd.DataFrame) -> tuple[bool, str, dict]:
    """Smart column detection for Excel/CSV files"""
    df.columns = [str(c).strip().lower() for c in df.columns]
    mapping = {}

    # Name column detection
    name_patterns = ["name", "customer", "person", "client", "contact", "full name"]
    for col in df.columns:
        if any(p in col for p in name_patterns):
            mapping["name"] = col
            break

    # Mobile column detection
    mobile_patterns = ["mobile", "phone", "whatsapp", "contact", "number", "cell", "tel", "no.", "no"]
    for col in df.columns:
        if any(p in col for p in mobile_patterns) and col != mapping.get("name"):
            mapping["mobile"] = col
            break

    # Email column detection
    for col in df.columns:
        if "email" in col or "mail" in col:
            mapping["email"] = col
            break

    # Validation
    if "name" not in mapping:
        return False, f"❌ No 'Name' column found.\n\nFound columns: `{list(df.columns)}`", mapping

    if "mobile" not in mapping and "email" not in mapping:
        return False, f"❌ Need at least 'Mobile' or 'Email' column.\n\nFound: `{list(df.columns)}`", mapping

    found = {v: k for k, v in mapping.items()}
    return True, f"✅ Detected → Name: `{mapping.get('name')}` | Mobile: `{mapping.get('mobile', 'N/A')}` | Email: `{mapping.get('email', 'N/A')}`", mapping

def clean_phone(num: str) -> str:
    """Clean and format phone number"""
    num = re.sub(r'[\s\-\+\(\)\.xe]', '', str(num).split(".")[0])
    if not num.isdigit():
        return ""
    if num.startswith("91") and len(num) == 12:
        return num
    if num.startswith("0") and len(num) == 11:
        return "91" + num[1:]
    if len(num) == 10:
        return "91" + num
    return num

def process_customers(df: pd.DataFrame, mapping: dict) -> list[dict]:
    """Convert DataFrame to customer list"""
    customers = []

    for idx, row in df.iterrows():
        def get_val(key):
            col = mapping.get(key)
            if col and col in row.index:
                val = str(row[col]).strip()
                return "" if val.lower() in ["nan", "nat", "none", "<na>", ""] else val
            return ""

        name = get_val("name") or f"Customer {idx + 1}"
        mobile = clean_phone(get_val("mobile")) if mapping.get("mobile") else ""
        email = get_val("email") if mapping.get("email") else ""

        # Skip entirely empty rows
        if not mobile and not email:
            continue

        customers.append({
            "id": idx,
            "name": name,
            "mobile": mobile,
            "email": email,
            "whatsapp_sent": False,
            "email_sent": False,
            "sent_at": None,
            "error": None,
        })

    return customers

# ─── MESSAGE HELPERS ─────────────────────────────────
def humanize_message(template: str, name: str, sender: str) -> str:
    """Add random variations to WhatsApp message"""
    greeting = random.choice(GREETINGS).format(name=name)
    msg = template.replace("{{name}}", name).replace("{{sender}}", sender)

    # Replace first line greeting if it starts with Hi/Hello/Hey
    lines = msg.split("\n", 1)
    if lines[0].startswith(("Hi", "Hello", "Hey", "Dear", "Good")):
        msg = greeting + ("\n" + lines[1] if len(lines) > 1 else "")

    msg = msg.strip() + f"\n\n— {sender}"

    # Randomly add emoji
    if random.random() > 0.4:
        msg += " " + random.choice(EMOJIS)

    return msg

def humanize_email(template: str, name: str, subject: str, sender: str) -> tuple[str, str]:
    """Add random variations to email"""
    greeting = random.choice(GREETINGS).format(name=name)

    # Random emoji prefix on subject
    if random.random() > 0.5:
        subject = random.choice(EMOJIS) + " " + subject

    body = template.replace("{{name}}", name).replace("{{sender}}", sender)
    body = re.sub(r'Hi \{\{name\}\}', greeting, body)
    subject = subject.replace("{{name}}", name)
    body += f"\n\n<p><em>Sent by <strong>{sender}</strong></em></p>"

    return subject, body

def get_send_stats(customers: list) -> tuple[int, int, int, int]:
    """Get sending statistics"""
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    sent_total = sum(1 for c in customers if c["whatsapp_sent"] or c["email_sent"])
    sent_hour = sum(1 for c in customers if c.get("sent_at") and c["sent_at"] > one_hour_ago)
    sent_today = sum(1 for c in customers if c.get("sent_at") and c["sent_at"] > today_start)
    pending = sum(1 for c in customers if not c["whatsapp_sent"] and not c["email_sent"])

    return sent_total, sent_hour, sent_today, pending

# ─── SENDING FUNCTIONS ───────────────────────────────
def send_whatsapp(mobile: str, message: str) -> tuple[bool, str]:
    """Send WhatsApp via pywhatkit"""
    try:
        import pywhatkit
        clean = clean_phone(mobile)
        if not clean:
            return False, "❌ Invalid phone number"
        pywhatkit.sendwhatmsg_instantly(f"+{clean}", message, tab_close=True, close_time=3)
        time.sleep(2)
        return True, "✅ WhatsApp sent!"
    except ImportError:
        return False, "❌ Install pywhatkit: `pip install pywhatkit`"
    except Exception as e:
        return False, f"❌ WhatsApp error: {str(e)[:80]}"

def send_email(
    to_email: str, subject: str, body: str,
    gmail_user: str, gmail_pass: str, sender_name: str
) -> tuple[bool, str]:
    """Send email via Gmail SMTP"""
    try:
        if not validate_email_format(to_email):
            return False, "❌ Invalid recipient email"

        # Create plain text version
        plain_text = re.sub(r'<[^>]+>', '', body).strip()

        msg = MIMEMultipart("alternative")
        msg["From"] = f"{sender_name} <{gmail_user}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["X-Mailer"] = "MarketAI"

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, to_email, msg.as_string())

        return True, "✅ Email sent!"
    except smtplib.SMTPAuthenticationError:
        return False, "❌ Gmail auth failed. Check App Password."
    except smtplib.SMTPRecipientsRefused:
        return False, "❌ Recipient email rejected."
    except Exception as e:
        return False, f"❌ Email error: {str(e)[:80]}"

# ============================================================
# AUTH PAGES (Not logged in)
# ============================================================
if not st.session_state["logged_in"]:

    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 MarketAI - Cloud Auto Sender</h1>
        <p>Send WhatsApp & Email campaigns automatically — 100% FREE</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup, tab_forgot = st.tabs(["🔓 Login", "📝 Sign Up", "🔑 Forgot Password"])

    # ── LOGIN TAB ──────────────────────────────────────
    with tab_login:
        st.subheader("Login to Your Account")

        with st.form("login_form"):
            login_email = st.text_input("📧 Email Address", placeholder="you@gmail.com")
            login_password = st.text_input("🔐 Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("🔓 Login", use_container_width=True, type="primary")

        if submitted:
            if not login_email or not login_password:
                st.error("❌ Please fill in all fields.")
            else:
                with st.spinner("Authenticating..."):
                    success, user_id, msg = login_user(login_email, login_password)
                if success:
                    st.session_state["logged_in"] = True
                    st.session_state["user_id"] = user_id
                    st.success(msg)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(msg)

    # ── SIGNUP TAB ─────────────────────────────────────
    with tab_signup:
        st.subheader("Create Free Account")

        if st.session_state["signup_step"] == 1:
            with st.form("signup_form"):
                st.write("**📋 Business Info**")
                col1, col2 = st.columns(2)
                with col1:
                    s_business = st.text_input("🏢 Business Name *", placeholder="My Shop")
                    s_email = st.text_input("📧 Email *", placeholder="you@gmail.com")
                    s_country = st.selectbox("🌍 Country *", list(COUNTRY_CODES.keys()))
                with col2:
                    s_phone = st.text_input("📱 Mobile Number *", placeholder="9876543210")
                    s_password = st.text_input("🔐 Password *", type="password", placeholder="Min 6 chars")
                    s_confirm = st.text_input("🔐 Confirm Password *", type="password")

                st.divider()
                st.write("**📧 Gmail Settings** _(for sending emails)_")
                st.info("💡 Use [Gmail App Password](https://myaccount.google.com/apppasswords), not your regular password.")

                col3, col4 = st.columns(2)
                with col3:
                    s_gmail = st.text_input("📧 Gmail Address *", placeholder="you@gmail.com")
                with col4:
                    s_gmail_pass = st.text_input("🔐 App Password *", type="password", placeholder="xxxx xxxx xxxx xxxx")

                submitted_signup = st.form_submit_button("📱 Send OTP to Mobile", use_container_width=True, type="primary")

            if submitted_signup:
                with st.spinner("Validating..."):
                    success, msg = signup_step1(
                        s_email, s_country, s_phone, s_password, s_confirm,
                        s_business, s_gmail, s_gmail_pass
                    )
                if success:
                    st.session_state["signup_step"] = 2
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        elif st.session_state["signup_step"] == 2:
            pending = st.session_state.get("pending_signup", {})
            st.info(f"📱 OTP sent to **{pending.get('phone', 'your phone')}**")
            st.warning("⏰ OTP expires in 10 minutes")

            with st.form("otp_form"):
                otp_input = st.text_input(
                    "🔐 Enter 6-digit OTP",
                    max_chars=6,
                    placeholder="123456"
                )
                col_a, col_b = st.columns(2)
                with col_a:
                    verify_btn = st.form_submit_button("✅ Verify & Create Account", type="primary", use_container_width=True)
                with col_b:
                    back_btn = st.form_submit_button("← Go Back", use_container_width=True)

            if verify_btn:
                if not otp_input or len(otp_input) != 6:
                    st.error("❌ Please enter the 6-digit OTP.")
                else:
                    with st.spinner("Verifying..."):
                        success, msg = complete_signup(otp_input)
                    if success:
                        st.session_state["signup_step"] = 1
                        st.success(msg)
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(msg)

            if back_btn:
                st.session_state["signup_step"] = 1
                st.rerun()

    # ── FORGOT PASSWORD TAB ────────────────────────────
    with tab_forgot:
        st.subheader("🔑 Reset Password")
        step = st.session_state["forgot_step"]

        # Step 1: Find Account
        if step == 1:
            method = st.radio(
                "Find your account by:",
                ["📧 Email Address", "📱 Phone Number"],
                horizontal=True
            )

            with st.form("forgot_form_1"):
                if method == "📧 Email Address":
                    f_email = st.text_input("📧 Registered Email", placeholder="you@gmail.com")
                    find_btn = st.form_submit_button("🔍 Find Account", use_container_width=True)

                    if find_btn:
                        user = find_user_by_email(f_email)
                        if user:
                            st.session_state["forgot_user_email"] = f_email.lower()
                            st.session_state["forgot_phone"] = user.get("phone")
                            st.session_state["forgot_step"] = 2
                            st.rerun()
                        else:
                            st.error("❌ No account found with that email.")

                else:
                    f_country = st.selectbox("🌍 Country", list(COUNTRY_CODES.keys()))
                    f_phone = st.text_input("📱 Mobile Number", placeholder="9876543210")
                    find_btn = st.form_submit_button("🔍 Find Account", use_container_width=True)

                    if find_btn:
                        full_phone, err = validate_phone(f_country, f_phone)
                        if not full_phone:
                            st.error(f"❌ {err}")
                        else:
                            email_found, user = find_user_by_phone(full_phone)
                            if user:
                                st.session_state["forgot_user_email"] = email_found
                                st.session_state["forgot_phone"] = full_phone
                                st.session_state["forgot_step"] = 2
                                st.rerun()
                            else:
                                st.error("❌ No account found with that phone number.")

        # Step 2: Send & Verify OTP
        elif step == 2:
            phone_display = st.session_state.get("forgot_phone", "")
            st.info(f"📱 Account found! Phone: **{phone_display}**")

            if not st.session_state.get("forgot_otp_sent"):
                if st.button("📲 Send OTP", use_container_width=True, type="primary"):
                    otp = generate_otp()
                    save_otp_supabase(phone_display, otp)
                    st.session_state["forgot_otp_sent"] = True
                    st.success(f"✅ OTP sent! **Your OTP: `{otp}`**")
                    st.rerun()
            else:
                with st.form("forgot_otp_form"):
                    f_otp = st.text_input("🔐 Enter OTP", max_chars=6, placeholder="123456")
                    verify_f = st.form_submit_button("✅ Verify OTP", use_container_width=True, type="primary")

                if verify_f:
                    ok, msg = verify_otp_supabase(phone_display, f_otp)
                    if ok:
                        st.session_state["forgot_step"] = 3
                        st.session_state["forgot_otp_sent"] = False
                        st.rerun()
                    else:
                        st.error(msg)

                if st.button("← Back to Find Account"):
                    st.session_state["forgot_step"] = 1
                    st.session_state["forgot_otp_sent"] = False
                    st.rerun()

        # Step 3: Set New Password
        elif step == 3:
            st.success("✅ Identity verified! Set your new password.")
            with st.form("new_password_form"):
                new_pass = st.text_input("🔐 New Password", type="password", placeholder="Min 6 chars")
                conf_pass = st.text_input("🔐 Confirm Password", type="password")
                reset_btn = st.form_submit_button("✅ Reset Password", use_container_width=True, type="primary")

            if reset_btn:
                if len(new_pass) < 6:
                    st.error("❌ Password must be at least 6 characters.")
                elif new_pass != conf_pass:
                    st.error("❌ Passwords do not match.")
                else:
                    success, msg = update_password(st.session_state["forgot_user_email"], new_pass)
                    if success:
                        # Reset all forgot state
                        for k in ["forgot_step", "forgot_user_email", "forgot_phone", "forgot_otp_sent"]:
                            st.session_state[k] = 1 if k == "forgot_step" else None
                        st.success("✅ Password reset! Please login.")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(msg)

    st.stop()

# ============================================================
# MAIN APP (Logged In)
# ============================================================
user_data = find_user_by_email(st.session_state["user_id"]) or {}
sender_name = user_data.get("business_name", "Your Business")
gmail_user = user_data.get("gmail_user", "")
gmail_pass = user_data.get("gmail_pass", "")

# ── Header ─────────────────────────────────────────
col_title, col_user, col_logout = st.columns([0.6, 0.25, 0.15])
with col_title:
    st.markdown(f"""
    <div class="main-header">
        <h2>🤖 {sender_name} Dashboard</h2>
        <p>📧 {st.session_state["user_id"]} | 📱 {user_data.get("phone", "N/A")}</p>
    </div>
    """, unsafe_allow_html=True)
with col_logout:
    if st.button("🚪 Logout", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ── Sidebar ────────────────────────────────────────
with st.sidebar:
    st.header("📁 Step 1: Load Contacts")

    # Sample download
    sample_df = pd.DataFrame({
        "Name": ["John Doe", "Jane Smith", "Bob Wilson"],
        "Mobile": ["9876543210", "9123456789", "9988776655"],
        "Email": ["john@example.com", "jane@example.com", "bob@example.com"]
    })
    st.download_button(
        label="📥 Download Sample Excel",
        data=sample_df.to_csv(index=False).encode("utf-8"),
        file_name="MarketAI_Template.csv",
        mime="text/csv",
        use_container_width=True
    )

    uploaded_file = st.file_uploader(
        "Upload Contacts File",
        type=["xlsx", "xls", "csv"],
        help="Upload Excel or CSV with Name, Mobile, Email columns"
    )

    if st.button("🗑️ Clear All Data", use_container_width=True):
        st.session_state["customers"] = []
        st.session_state["sending_active"] = False
        st.rerun()

    st.divider()
    st.header("✉️ Step 2: Message Templates")

    send_mode = st.radio(
        "Send via:",
        ["📱 WhatsApp", "📧 Email", "📱+📧 Both"],
        horizontal=False
    )

    if "WhatsApp" in send_mode or "Both" in send_mode:
        whatsapp_template = st.text_area(
            "WhatsApp Message:",
            value="Hi {{name}},\n\nWe have a special offer just for you! 🎉\n\nContact us today!",
            height=120,
            help="Use {{name}} for customer name, {{sender}} for your business name"
        )

    if "Email" in send_mode or "Both" in send_mode:
        email_subject = st.text_input(
            "Email Subject:",
            value="Special Offer for {{name}}! 🎉"
        )
        email_body = st.text_area(
            "Email Body (HTML):",
            value="<h2>Hi {{name}},</h2>\n<p>We have an <strong>exclusive offer</strong> for you!</p>\n<p>Contact us today! 🚀</p>",
            height=150,
            help="Supports HTML formatting"
        )

    st.divider()
    st.header("⚙️ Step 3: Speed Settings")

    max_per_hour = st.slider("Max messages per hour:", 5, 50, 20, help="Stay under limits to avoid bans")
    max_per_day = st.slider("Max messages per day:", 10, 200, 80)
    add_variations = st.checkbox("🎲 Randomize messages", True, help="Adds slight variations to avoid spam detection")

    st.divider()
    st.caption(f"🏢 {sender_name} | 📧 {gmail_user}")

# ── File Upload Processing ─────────────────────────
if uploaded_file and not st.session_state["customers"]:
    try:
        with st.spinner("Reading file..."):
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file, engine="openpyxl")

        is_valid, msg, mapping = detect_columns(df)

        if is_valid:
            st.success(msg)

            # Preview
            with st.expander("👀 Preview Data (first 5 rows)", expanded=True):
                # Show with detected columns highlighted
                display_cols = [v for v in mapping.values()]
                st.dataframe(df.head(5), use_container_width=True)
                st.caption(f"📊 Total rows: **{len(df)}**")

            col_load, col_skip = st.columns(2)
            with col_load:
                if st.button("📥 Load All Contacts", use_container_width=True, type="primary"):
                    customers = process_customers(df, mapping)
                    if customers:
                        st.session_state["customers"] = customers
                        st.success(f"✅ Loaded **{len(customers)}** contacts!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ No valid contacts found in file.")
        else:
            st.error(msg)
            with st.expander("🔍 Debug Info"):
                st.write("Columns found:", list(df.columns))
                st.dataframe(df.head(3))

    except ImportError:
        st.error("❌ Missing `openpyxl`. Run: `pip install openpyxl`")
    except Exception as e:
        st.error(f"❌ File read error: {e}")

# ── Main Dashboard ─────────────────────────────────
if st.session_state["customers"]:
    customers = st.session_state["customers"]
    sent_total, sent_hour, sent_today, pending = get_send_stats(customers)

    # Stats Row
    st.subheader("📊 Campaign Stats")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 Total Contacts", len(customers))
    c2.metric("✅ Sent Total", sent_total)
    c3.metric("⏳ Pending", pending)
    c4.metric("⏱️ Last Hour", f"{sent_hour}/{max_per_hour}")
    c5.metric("📅 Today", f"{sent_today}/{max_per_day}")

    # Progress bar
    if len(customers) > 0:
        progress = sent_total / len(customers)
        st.progress(progress, text=f"Campaign Progress: {sent_total}/{len(customers)} ({progress*100:.1f}%)")

    st.divider()

    # Control Buttons
    col_start, col_stop, col_reset = st.columns([0.4, 0.3, 0.3])
    with col_start:
        if not st.session_state["sending_active"]:
            if st.button("▶️ START AUTO SENDING", use_container_width=True, type="primary"):
                if not gmail_user or not gmail_pass:
                    st.error("❌ Gmail credentials missing. Please update your profile.")
                else:
                    st.session_state["sending_active"] = True
                    st.rerun()
        else:
            st.success("🟢 **Sending Active...**")

    with col_stop:
        if st.session_state["sending_active"]:
            if st.button("⏹️ PAUSE SENDING", use_container_width=True, type="secondary"):
                st.session_state["sending_active"] = False
                st.rerun()

    with col_reset:
        if st.button("🔄 Reset Sent Status", use_container_width=True):
            for c in customers:
                c["whatsapp_sent"] = False
                c["email_sent"] = False
                c["sent_at"] = None
                c["error"] = None
            st.session_state["sending_active"] = False
            st.rerun()

    # ── SENDING LOOP ──────────────────────────────
    if st.session_state["sending_active"]:
        # Check limits
        if sent_hour >= max_per_hour:
            st.session_state["sending_active"] = False
            st.warning(f"⚠️ Hourly limit reached ({max_per_hour}/hr). Auto-paused. Try again later.")
            st.rerun()

        if sent_today >= max_per_day:
            st.session_state["sending_active"] = False
            st.warning(f"⚠️ Daily limit reached ({max_per_day}/day). Auto-paused.")
            st.rerun()

        # Find next unsent contact
        next_contact = None
        wa_mode = "WhatsApp" in send_mode or "Both" in send_mode
        email_mode = "Email" in send_mode or "Both" in send_mode

        for c in customers:
            needs_wa = wa_mode and c["mobile"] and not c["whatsapp_sent"]
            needs_email = email_mode and c["email"] and not c["email_sent"]
            if needs_wa or needs_email:
                next_contact = c
                break

        if next_contact:
            status_placeholder = st.empty()
            status_placeholder.info(f"📤 Sending to: **{next_contact['name']}**...")

            # Send WhatsApp
            if wa_mode and next_contact["mobile"] and not next_contact["whatsapp_sent"]:
                if add_variations:
                    msg_text = humanize_message(whatsapp_template, next_contact["name"], sender_name)
                else:
                    msg_text = whatsapp_template.replace("{{name}}", next_contact["name"])

                ok, resp = send_whatsapp(next_contact["mobile"], msg_text)
                next_contact["whatsapp_sent"] = ok
                if not ok:
                    next_contact["error"] = resp
                    status_placeholder.warning(f"⚠️ WhatsApp to {next_contact['name']}: {resp}")

            # Send Email
            if email_mode and next_contact["email"] and not next_contact["email_sent"]:
                if add_variations:
                    subj, body = humanize_email(email_body, next_contact["name"], email_subject, sender_name)
                else:
                    subj = email_subject.replace("{{name}}", next_contact["name"])
                    body = email_body.replace("{{name}}", next_contact["name"])

                ok, resp = send_email(next_contact["email"], subj, body, gmail_user, gmail_pass, sender_name)
                next_contact["email_sent"] = ok
                if not ok:
                    next_contact["error"] = resp
                    status_placeholder.warning(f"⚠️ Email to {next_contact['name']}: {resp}")

            # Update sent time
            if next_contact["whatsapp_sent"] or next_contact["email_sent"]:
                next_contact["sent_at"] = datetime.now()
                status_placeholder.success(f"✅ Sent to **{next_contact['name']}** successfully!")

            # Human delay
            delay = random.randint(HUMAN_DELAY_MIN, HUMAN_DELAY_MAX)
            with st.spinner(f"⏳ Waiting {delay}s before next send (human-like delay)..."):
                time.sleep(delay)

            st.rerun()

        else:
            # All done!
            st.session_state["sending_active"] = False
            st.success("🎉 Campaign Complete! All messages sent.")
            st.balloons()
            st.rerun()

    # ── Contact Table ──────────────────────────────
    st.divider()
    st.subheader("📋 Contact List")

    # Filter options
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        status_filter = st.selectbox(
            "Filter by status:",
            ["All", "✅ Sent", "⏳ Pending", "❌ Failed"]
        )
    with filter_col2:
        search_term = st.text_input("🔍 Search by name/email/phone:", placeholder="Search...")

    # Apply filters
    filtered = customers.copy()
    if status_filter == "✅ Sent":
        filtered = [c for c in filtered if c["whatsapp_sent"] or c["email_sent"]]
    elif status_filter == "⏳ Pending":
        filtered = [c for c in filtered if not c["whatsapp_sent"] and not c["email_sent"]]
    elif status_filter == "❌ Failed":
        filtered = [c for c in filtered if c.get("error")]

    if search_term:
        st._lower = search_term.lower()
        filtered = [
            c for c in filtered
            if search_term.lower() in c["name"].lower()
            or search_term.lower() in c["email"].lower()
            or search_term.lower() in c["mobile"]
        ]

    # Build display DataFrame
    table_data = []
    for c in filtered[:100]:  # Show max 100 rows
        table_data.append({
            "Name": c["name"],
            "Mobile": c["mobile"] or "—",
            "Email": c["email"] or "—",
            "WhatsApp": "✅" if c["whatsapp_sent"] else "⏳",
            "Email Sent": "✅" if c["email_sent"] else "⏳",
            "Sent At": c["sent_at"].strftime("%H:%M:%S") if c.get("sent_at") else "—",
            "Error": c.get("error") or "—",
        })

    if table_data:
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, height=400)
        if len(filtered) > 100:
            st.caption(f"Showing 100 of {len(filtered)} contacts.")
    else:
        st.info("No contacts match the filter.")

    # Export results
    if sent_total > 0:
        st.divider()
        export_df = pd.DataFrame([{
            "Name": c["name"],
            "Mobile": c["mobile"],
            "Email": c["email"],
            "WhatsApp Sent": c["whatsapp_sent"],
            "Email Sent": c["email_sent"],
            "Sent At": str(c.get("sent_at") or ""),
            "Error": c.get("error") or ""
        } for c in customers])

        st.download_button(
            label="📥 Export Results CSV",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name=f"MarketAI_Results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    # Empty state
    st.markdown("""
    <div style="text-align:center; padding: 60px; color: #666;">
        <h2>📁 No Contacts Loaded</h2>
        <p>Upload an Excel/CSV file using the sidebar to get started.</p>
        <p>Download the sample template to see the required format.</p>
    </div>
    """, unsafe_allow_html=True)
