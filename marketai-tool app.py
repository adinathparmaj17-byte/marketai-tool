# ============================================================
# MarketAI - 100% FREE WhatsApp & Email Marketing Tool
# CLOUD VERSION (Supabase Integrated) + Smart Excel Reader
# ============================================================

# ─── Safe Import Check First ────────────────────────
import sys
import subprocess
import importlib

def check_and_install(package_name, import_name=None):
    """Check if package exists, show clear error if not"""
    import_name = import_name or package_name
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False

import streamlit as st

# ─── Page Config (MUST be first streamlit command) ──
st.set_page_config(
    page_title="MarketAI - FREE Sender",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Check Required Packages ────────────────────────
missing_packages = []

required_packages = {
    "supabase": "supabase",
    "pandas": "pandas",
    "openpyxl": "openpyxl",
}

for pkg, import_name in required_packages.items():
    if not check_and_install(pkg, import_name):
        missing_packages.append(pkg)

if missing_packages:
    st.error("🚨 **Missing Required Packages!**")
    st.markdown(f"""
    ### Fix This Error:
    
    **Option 1: Add to `requirements.txt`** _(Streamlit Cloud)_
    
    Create a file called `requirements.txt` in your GitHub repo root with:
    ```
    streamlit>=1.28.0
    supabase>=2.0.0
    pandas>=2.0.0
    openpyxl>=3.1.0
    pywhatkit>=5.4
    ```
    
    **Option 2: Install manually** _(Local machine)_
    ```bash
    pip install {' '.join(missing_packages)}
    ```
    
    **Missing packages:** `{', '.join(missing_packages)}`
    
    ---
    After adding `requirements.txt`, **push to GitHub** and 
    **reboot your Streamlit Cloud app** from the dashboard.
    """)
    st.stop()

# ─── Now safe to import everything ──────────────────
import pandas as pd
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

# Supabase import with clear error
try:
    from supabase import create_client, Client
except ImportError:
    st.error("❌ `supabase` package not found!")
    st.code("pip install supabase", language="bash")
    st.stop()

# ─── Custom CSS ──────────────────────────────────────
st.markdown("""
<style>
    /* Main header gradient */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px 25px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
    }
    .main-header h2 { margin: 0; font-size: 1.8rem; }
    .main-header p  { margin: 5px 0 0; opacity: 0.85; }

    /* Cards */
    .info-card {
        background: #f8f9ff;
        border: 1px solid #e0e4ff;
        border-left: 4px solid #667eea;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }

    /* Success / Warning boxes */
    .success-msg {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 12px;
        border-radius: 8px;
        color: #155724;
        font-weight: 500;
    }

    /* Hide streamlit branding */
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── SUPABASE CONNECTION ─────────────────────────────
@st.cache_resource
def init_supabase():
    """Initialize Supabase with helpful error messages"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        client = create_client(url, key)
        return client, None
    except KeyError as e:
        return None, f"Missing secret key: {e}"
    except Exception as e:
        return None, str(e)

supabase, conn_error = init_supabase()

if not supabase:
    st.error("⚠️ **Cannot connect to Supabase!**")
    st.markdown(f"""
    **Error:** `{conn_error}`
    
    ### Fix:
    Create `.streamlit/secrets.toml` in your project:
    ```toml
    SUPABASE_URL = "https://your-project.supabase.co"
    SUPABASE_KEY = "your-anon-key-here"
    ```
    
    Or on **Streamlit Cloud**:
    1. Go to your app → **⋮ Menu** → **Settings**
    2. Click **Secrets** tab
    3. Add:
    ```
    SUPABASE_URL = "https://xxxx.supabase.co"
    SUPABASE_KEY = "eyJ..."
    ```
    """)
    st.stop()

# ─── CONSTANTS ────────────────────────────────────────
COUNTRY_CODES = {
    "🇮🇳 India (+91)"        : "+91",
    "🇵🇰 Pakistan (+92)"     : "+92",
    "🇧🇩 Bangladesh (+880)"  : "+880",
    "🇬🇧 UK (+44)"           : "+44",
    "🇺🇸 USA (+1)"           : "+1",
    "🇨🇦 Canada (+1)"        : "+1",
    "🇦🇺 Australia (+61)"    : "+61",
    "🇳🇿 New Zealand (+64)"  : "+64",
    "🇿🇦 South Africa (+27)" : "+27",
    "🇩🇪 Germany (+49)"      : "+49",
    "🇫🇷 France (+33)"       : "+33",
    "🇮🇹 Italy (+39)"        : "+39",
    "🇪🇸 Spain (+34)"        : "+34",
    "🇸🇬 Singapore (+65)"    : "+65",
    "🇲🇾 Malaysia (+60)"     : "+60",
    "🇦🇪 UAE (+971)"         : "+971",
    "🇸🇦 Saudi Arabia (+966)": "+966",
    "🇳🇬 Nigeria (+234)"     : "+234",
    "🇰🇪 Kenya (+254)"       : "+254",
    "🇧🇷 Brazil (+55)"       : "+55",
}

GREETINGS = [
    "Hi {name}!", "Hello {name},", "Hey {name}!",
    "Hi there {name}!", "Hello {name} 👋", "Hey {name} 🙌",
    "Dear {name},", "Good day {name}!",
]

EMOJIS = ["🎉","🔥","💥","✨","🎊","🚀","💪","👋","⭐","🎯","💎","🎁"]

HUMAN_DELAY_MIN = 30
HUMAN_DELAY_MAX = 120

# ─── SECURITY HELPERS ────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))

# ─── VALIDATION HELPERS ──────────────────────────────
def validate_email_format(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(email).strip()))

def validate_phone(country: str, phone: str):
    phone_clean = re.sub(r'[\s\-\+\(\)]', '', str(phone))
    country_code = COUNTRY_CODES.get(country, "").replace("+", "")
    if not country_code:
        return None, "Invalid country"
    if not phone_clean.isdigit():
        return None, "Only digits allowed"
    if len(phone_clean) < 7:
        return None, "Too short"
    if len(phone_clean) > 15:
        return None, "Too long"
    if phone_clean.startswith(country_code):
        phone_clean = phone_clean[len(country_code):]
    return f"+{country_code}{phone_clean}", "Valid"

# ─── OTP STORAGE (Supabase + Session fallback) ───────
def save_otp(phone: str, otp: str) -> bool:
    try:
        expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
        supabase.table("otp_verifications").upsert(
            {"phone": phone, "otp": otp, "expiry": expiry},
            on_conflict="phone"
        ).execute()
        return True
    except Exception:
        # Session fallback
        if "otp_store" not in st.session_state:
            st.session_state["otp_store"] = {}
        st.session_state["otp_store"][phone] = {
            "otp": otp,
            "expiry": (datetime.now() + timedelta(minutes=10)).isoformat()
        }
        return True

def get_and_delete_otp(phone: str):
    """Returns (otp, expiry_str) or (None, None)"""
    try:
        resp = supabase.table("otp_verifications").select("*").eq("phone", phone).execute()
        if resp.data:
            record = resp.data[0]
            supabase.table("otp_verifications").delete().eq("phone", phone).execute()
            return record["otp"], record["expiry"]
    except Exception:
        pass

    # Session fallback
    store = st.session_state.get("otp_store", {})
    if phone in store:
        record = store.pop(phone)
        return record["otp"], record["expiry"]

    return None, None

def verify_otp(phone: str, otp_input: str):
    saved_otp, expiry_str = get_and_delete_otp(phone)
    if not saved_otp:
        return False, "❌ OTP not found. Request a new one."
    if str(otp_input).strip() != str(saved_otp).strip():
        return False, "❌ Incorrect OTP."
    if datetime.now() > datetime.fromisoformat(expiry_str):
        return False, "❌ OTP expired. Request a new one."
    return True, "✅ OTP verified!"

# ─── DATABASE FUNCTIONS ──────────────────────────────
@st.cache_data(ttl=30)
def find_user_by_email(email: str):
    try:
        r = supabase.table("users").select("*").eq("email", email.lower().strip()).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        return None

def find_user_by_phone(phone: str):
    try:
        r = supabase.table("users").select("*").eq("phone", phone).execute()
        if r.data:
            u = r.data[0]
            return u["email"], u
    except Exception:
        pass
    return None, None

def save_new_user(data: dict):
    try:
        data["password"] = hash_password(data["password"])
        data["created_at"] = datetime.now().isoformat()
        supabase.table("users").insert(data).execute()
        find_user_by_email.clear()
        return True, "✅ Account created!"
    except Exception as e:
        err = str(e)
        if "duplicate" in err.lower() or "unique" in err.lower():
            return False, "❌ Email or phone already registered."
        return False, f"❌ Database error: {err[:100]}"

def update_password_db(email: str, new_password: str):
    try:
        supabase.table("users").update(
            {"password": hash_password(new_password)}
        ).eq("email", email).execute()
        find_user_by_email.clear()
        return True, "✅ Password updated!"
    except Exception as e:
        return False, f"❌ Error: {e}"

# ─── AUTH FUNCTIONS ───────────────────────────────────
def do_signup_step1(email, country, phone, password, confirm, business, gmail, gpass):
    if not business or len(business.strip()) < 2:
        return False, "❌ Business name needs 2+ characters."
    if not validate_email_format(email):
        return False, "❌ Invalid email format."
    if find_user_by_email(email):
        return False, "❌ Email already registered."

    full_phone, pmsg = validate_phone(country, phone)
    if not full_phone:
        return False, f"❌ Phone error: {pmsg}"

    _, existing = find_user_by_phone(full_phone)
    if existing:
        return False, "❌ Phone number already registered."

    if not password or len(password) < 6:
        return False, "❌ Password needs 6+ characters."
    if password != confirm:
        return False, "❌ Passwords don't match."
    if not validate_email_format(gmail):
        return False, "❌ Invalid Gmail address."
    if not gpass or len(gpass) < 8:
        return False, "❌ Gmail App Password needs 8+ characters."

    otp = generate_otp()
    save_otp(full_phone, otp)

    st.session_state["pending_signup"] = {
        "email"        : email.lower().strip(),
        "country"      : country,
        "phone"        : full_phone,
        "password"     : password,
        "business_name": business.strip(),
        "gmail_user"   : gmail.strip(),
        "gmail_pass"   : gpass,
    }
    return True, (
        f"📲 OTP for **{full_phone}**: `{otp}`\n\n"
        "_In production this would be sent via SMS (Twilio/MSG91)._"
    )

def do_complete_signup(otp_input: str):
    pending = st.session_state.get("pending_signup", {})
    if not pending:
        return False, "❌ Session expired. Start over."

    ok, msg = verify_otp(pending["phone"], otp_input)
    if not ok:
        return False, msg

    success, message = save_new_user(dict(pending))
    if success:
        st.session_state.pop("pending_signup", None)
    return success, message

def do_login(email: str, password: str):
    if not email or not password:
        return False, None, "❌ Enter email and password."
    if not validate_email_format(email):
        return False, None, "❌ Invalid email format."
    user = find_user_by_email(email.lower().strip())
    if user and user["password"] == hash_password(password):
        return True, user["email"], f"✅ Welcome back, **{user['business_name']}**!"
    return False, None, "❌ Wrong email or password."

# ─── SESSION STATE ────────────────────────────────────
DEFAULTS = {
    "logged_in"       : False,
    "user_id"         : None,
    "customers"       : [],
    "sending_active"  : False,
    "signup_step"     : 1,
    "forgot_step"     : 1,
    "forgot_email"    : None,
    "forgot_phone"    : None,
    "forgot_otp_sent" : False,
    "pending_signup"  : {},
    "otp_store"       : {},
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── EXCEL / CSV PROCESSING ──────────────────────────
def detect_columns(df: pd.DataFrame):
    df.columns = [str(c).strip().lower() for c in df.columns]
    mapping = {}

    for col in df.columns:
        if any(p in col for p in ["name","customer","person","client","contact name"]):
            mapping["name"] = col; break

    for col in df.columns:
        if any(p in col for p in ["mobile","phone","whatsapp","cell","tel","contact","number"]):
            if col != mapping.get("name"):
                mapping["mobile"] = col; break

    for col in df.columns:
        if "email" in col or "mail" in col:
            mapping["email"] = col; break

    if "name" not in mapping:
        return False, f"❌ No Name column found. Columns: `{list(df.columns)}`", mapping
    if "mobile" not in mapping and "email" not in mapping:
        return False, f"❌ Need Mobile or Email column. Columns: `{list(df.columns)}`", mapping

    info = (f"✅ Name→`{mapping.get('name')}` | "
            f"Mobile→`{mapping.get('mobile','—')}` | "
            f"Email→`{mapping.get('email','—')}`")
    return True, info, mapping

def clean_phone_number(num: str) -> str:
    num = re.sub(r'[\s\-\+\(\)\.xe]', '', str(num).split(".")[0])
    if not num.isdigit(): return ""
    if num.startswith("91") and len(num) == 12: return num
    if num.startswith("0") and len(num) == 11:  return "91" + num[1:]
    if len(num) == 10: return "91" + num
    return num

def process_excel(df: pd.DataFrame, mapping: dict) -> list:
    customers = []
    BAD_VALS = {"nan","nat","none","<na>","","n/a","null"}

    for idx, row in df.iterrows():
        def get(key):
            col = mapping.get(key)
            if col and col in row.index:
                v = str(row[col]).strip()
                return "" if v.lower() in BAD_VALS else v
            return ""

        name   = get("name")   or f"Customer {idx+1}"
        mobile = clean_phone_number(get("mobile")) if mapping.get("mobile") else ""
        email  = get("email").lower() if mapping.get("email") else ""

        if not mobile and not email:
            continue

        customers.append({
            "id"           : idx,
            "name"         : name,
            "mobile"       : mobile,
            "email"        : email,
            "whatsapp_sent": False,
            "email_sent"   : False,
            "sent_at"      : None,
            "error"        : None,
        })
    return customers

# ─── MESSAGING HELPERS ───────────────────────────────
def humanize_whatsapp(template: str, name: str, sender: str) -> str:
    greeting = random.choice(GREETINGS).format(name=name)
    msg = template.replace("{{name}}", name).replace("{{sender}}", sender)
    lines = msg.split("\n", 1)
    if lines[0].startswith(("Hi","Hello","Hey","Dear","Good")):
        msg = greeting + ("\n" + lines[1] if len(lines) > 1 else "")
    msg = msg.strip() + f"\n\n— {sender}"
    if random.random() > 0.4:
        msg += " " + random.choice(EMOJIS)
    return msg

def humanize_email(template: str, name: str, subject: str, sender: str):
    greeting = random.choice(GREETINGS).format(name=name)
    if random.random() > 0.5:
        subject = random.choice(EMOJIS) + " " + subject
    body = template.replace("{{name}}", name).replace("{{sender}}", sender)
    body = re.sub(r'Hi \{\{name\}\}', greeting, body)
    subject = subject.replace("{{name}}", name)
    body += f"\n\n<p><em>Sent by <strong>{sender}</strong></em></p>"
    return subject, body

def get_stats(customers: list):
    now = datetime.now()
    one_hr  = now - timedelta(hours=1)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    total   = len(customers)
    sent    = sum(1 for c in customers if c["whatsapp_sent"] or c["email_sent"])
    per_hr  = sum(1 for c in customers if c.get("sent_at") and c["sent_at"] > one_hr)
    per_day = sum(1 for c in customers if c.get("sent_at") and c["sent_at"] > day_start)
    pending = total - sent
    return total, sent, per_hr, per_day, pending

# ─── SEND FUNCTIONS ──────────────────────────────────
def send_whatsapp(mobile: str, message: str):
    try:
        import pywhatkit
        num = clean_phone_number(mobile)
        if not num:
            return False, "❌ Invalid phone number"
        pywhatkit.sendwhatmsg_instantly(f"+{num}", message, tab_close=True, close_time=3)
        time.sleep(2)
        return True, "✅ Sent!"
    except ImportError:
        return False, "❌ Install pywhatkit: pip install pywhatkit"
    except Exception as e:
        return False, f"❌ {str(e)[:80]}"

def send_email_smtp(to: str, subject: str, body: str, gmail_user: str, gmail_pass: str, sender: str):
    try:
        if not validate_email_format(to):
            return False, "❌ Invalid email address"
        plain = re.sub(r'<[^>]+>', '', body).strip()
        msg = MIMEMultipart("alternative")
        msg["From"]    = f"{sender} <{gmail_user}>"
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(body,  "html"))
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
            s.ehlo(); s.starttls()
            s.login(gmail_user, gmail_pass)
            s.sendmail(gmail_user, to, msg.as_string())
        return True, "✅ Sent!"
    except smtplib.SMTPAuthenticationError:
        return False, "❌ Gmail auth failed — check App Password"
    except Exception as e:
        return False, f"❌ {str(e)[:80]}"

# ============================================================
# AUTH PAGES
# ============================================================
if not st.session_state["logged_in"]:

    st.markdown("""
    <div class="main-header">
        <h2>🤖 MarketAI — Cloud Auto Sender</h2>
        <p>Send WhatsApp & Email campaigns automatically · 100% FREE</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup, tab_forgot = st.tabs(["🔓 Login", "📝 Sign Up", "🔑 Forgot Password"])

    # ──────── LOGIN ────────────────────────────────────
    with tab_login:
        st.subheader("Login")
        with st.form("login_form", clear_on_submit=False):
            le = st.text_input("📧 Email", placeholder="you@gmail.com")
            lp = st.text_input("🔐 Password", type="password")
            login_btn = st.form_submit_button("🔓 Login", use_container_width=True, type="primary")

        if login_btn:
            with st.spinner("Checking credentials..."):
                ok, uid, msg = do_login(le, lp)
            if ok:
                st.session_state["logged_in"] = True
                st.session_state["user_id"]   = uid
                st.success(msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)

    # ──────── SIGN UP ──────────────────────────────────
    with tab_signup:
        st.subheader("Create Free Account")

        if st.session_state["signup_step"] == 1:
            with st.form("signup_form"):
                st.write("**Business Info**")
                c1, c2 = st.columns(2)
                with c1:
                    sb = st.text_input("🏢 Business Name *")
                    se = st.text_input("📧 Email *")
                    sc = st.selectbox("🌍 Country *", list(COUNTRY_CODES.keys()))
                with c2:
                    sp  = st.text_input("📱 Mobile *", placeholder="9876543210")
                    spw = st.text_input("🔐 Password *", type="password")
                    spc = st.text_input("🔐 Confirm *", type="password")

                st.divider()
                st.write("**Gmail Settings** _(for email sending)_")
                st.caption("Use Gmail App Password — not your regular password")

                c3, c4 = st.columns(2)
                with c3: sg  = st.text_input("📧 Gmail Address *")
                with c4: sgp = st.text_input("🔐 App Password *", type="password")

                otp_btn = st.form_submit_button(
                    "📱 Send OTP & Continue",
                    use_container_width=True, type="primary"
                )

            if otp_btn:
                with st.spinner("Validating..."):
                    ok, msg = do_signup_step1(se, sc, sp, spw, spc, sb, sg, sgp)
                if ok:
                    st.session_state["signup_step"] = 2
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        elif st.session_state["signup_step"] == 2:
            pending = st.session_state.get("pending_signup", {})
            st.info(f"📱 OTP sent to **{pending.get('phone')}** — valid 10 mins")

            with st.form("otp_form"):
                oi = st.text_input("🔐 Enter 6-digit OTP", max_chars=6, placeholder="123456")
                ca, cb = st.columns(2)
                with ca: vbtn = st.form_submit_button("✅ Verify & Create Account", type="primary", use_container_width=True)
                with cb: bbtn = st.form_submit_button("← Back", use_container_width=True)

            if vbtn:
                if len(str(oi).strip()) != 6:
                    st.error("❌ OTP must be 6 digits.")
                else:
                    with st.spinner("Creating account..."):
                        ok, msg = do_complete_signup(oi)
                    if ok:
                        st.session_state["signup_step"] = 1
                        st.success(msg)
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(msg)

            if bbtn:
                st.session_state["signup_step"] = 1
                st.rerun()

    # ──────── FORGOT PASSWORD ──────────────────────────
    with tab_forgot:
        st.subheader("🔑 Reset Password")
        step = st.session_state["forgot_step"]

        if step == 1:
            method = st.radio("Find account by:", ["📧 Email", "📱 Phone"], horizontal=True)
            with st.form("forgot_find"):
                if method == "📧 Email":
                    fe = st.text_input("📧 Registered Email")
                    fb = st.form_submit_button("🔍 Find", use_container_width=True)
                    if fb:
                        u = find_user_by_email(fe)
                        if u:
                            st.session_state.update({"forgot_email": u["email"], "forgot_phone": u["phone"], "forgot_step": 2})
                            st.rerun()
                        else: st.error("❌ Not found.")
                else:
                    fc = st.selectbox("🌍 Country", list(COUNTRY_CODES.keys()))
                    fp = st.text_input("📱 Mobile")
                    fb = st.form_submit_button("🔍 Find", use_container_width=True)
                    if fb:
                        fph, _ = validate_phone(fc, fp)
                        em, u  = find_user_by_phone(fph) if fph else (None, None)
                        if u:
                            st.session_state.update({"forgot_email": em, "forgot_phone": fph, "forgot_step": 2})
                            st.rerun()
                        else: st.error("❌ Not found.")

        elif step == 2:
            phone_disp = st.session_state["forgot_phone"]
            st.info(f"Account found! Phone: **{phone_disp}**")

            if not st.session_state["forgot_otp_sent"]:
                if st.button("📲 Send OTP", type="primary", use_container_width=True):
                    otp = generate_otp()
                    save_otp(phone_disp, otp)
                    st.session_state["forgot_otp_sent"] = True
                    st.success(f"✅ OTP sent! Code: `{otp}`")
                    st.rerun()
            else:
                with st.form("forgot_otp"):
                    fo = st.text_input("🔐 Enter OTP", max_chars=6)
                    fv = st.form_submit_button("✅ Verify", type="primary", use_container_width=True)
                if fv:
                    ok, msg = verify_otp(phone_disp, fo)
                    if ok:
                        st.session_state.update({"forgot_step": 3, "forgot_otp_sent": False})
                        st.rerun()
                    else: st.error(msg)

                if st.button("← Back"):
                    st.session_state.update({"forgot_step": 1, "forgot_otp_sent": False})
                    st.rerun()

        elif step == 3:
            st.success("✅ Identity confirmed!")
            with st.form("new_pass_form"):
                np1 = st.text_input("🔐 New Password", type="password")
                np2 = st.text_input("🔐 Confirm", type="password")
                rb  = st.form_submit_button("✅ Reset Password", type="primary", use_container_width=True)
            if rb:
                if len(np1) < 6:
                    st.error("❌ Needs 6+ characters.")
                elif np1 != np2:
                    st.error("❌ Don't match.")
                else:
                    ok, msg = update_password_db(st.session_state["forgot_email"], np1)
                    if ok:
                        for k in ["forgot_step","forgot_email","forgot_phone","forgot_otp_sent"]:
                            st.session_state[k] = 1 if k == "forgot_step" else None
                        st.success("✅ Password reset! Please login.")
                        time.sleep(2); st.rerun()
                    else: st.error(msg)

    st.stop()

# ============================================================
# MAIN APP (Logged In)
# ============================================================
user_data   = find_user_by_email(st.session_state["user_id"]) or {}
sender_name = user_data.get("business_name", "My Business")
gmail_user  = user_data.get("gmail_user", "")
gmail_pass  = user_data.get("gmail_pass", "")

# Header
col_h, col_lg = st.columns([0.85, 0.15])
with col_h:
    st.markdown(f"""
    <div class="main-header">
        <h2>🤖 {sender_name}</h2>
        <p>📧 {st.session_state["user_id"]} | 📱 {user_data.get("phone","—")}</p>
    </div>
    """, unsafe_allow_html=True)
with col_lg:
    st.write("")
    st.write("")
    if st.button("🚪 Logout", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ── SIDEBAR ───────────────────────────────────────────
with st.sidebar:
    st.header("📁 Upload Contacts")

    sample = pd.DataFrame({
        "Name"  : ["John Doe","Jane Smith","Bob Wilson"],
        "Mobile": ["9876543210","9123456789","9988776655"],
        "Email" : ["john@example.com","jane@example.com","bob@example.com"]
    })
    st.download_button(
        "📥 Download Sample Template",
        data=sample.to_csv(index=False).encode(),
        file_name="MarketAI_Template.csv",
        mime="text/csv",
        use_container_width=True
    )

    uploaded = st.file_uploader("Upload Excel / CSV", type=["xlsx","xls","csv"])

    if st.button("🗑️ Clear All Data", use_container_width=True):
        st.session_state["customers"]       = []
        st.session_state["sending_active"]  = False
        st.rerun()

    st.divider()
    st.header("✉️ Message Templates")

    send_mode = st.radio("Send via:", ["📱 WhatsApp","📧 Email","📱+📧 Both"])

    wa_template = em_subject = em_body = ""

    if "WhatsApp" in send_mode or "Both" in send_mode:
        wa_template = st.text_area(
            "WhatsApp Message:",
            "Hi {{name}},\n\nWe have a special offer just for you! 🎉\n\nContact us today!",
            height=110,
            help="Use {{name}} and {{sender}}"
        )

    if "Email" in send_mode or "Both" in send_mode:
        em_subject = st.text_input("Email Subject:", "Special Offer for {{name}}! 🎉")
        em_body    = st.text_area(
            "Email Body (HTML):",
            "<h2>Hi {{name}},</h2>\n<p>We have an <strong>exclusive offer</strong> just for you!</p>",
            height=120
        )

    st.divider()
    st.header("⚙️ Speed Settings")
    max_hr  = st.slider("Max per hour:", 5, 50, 20)
    max_day = st.slider("Max per day:",  10, 200, 80)
    do_vary = st.checkbox("🎲 Randomize messages", True)

# ── FILE UPLOAD PROCESSING ────────────────────────────
if uploaded and not st.session_state["customers"]:
    try:
        with st.spinner("Reading file..."):
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded, engine="openpyxl")

        ok, info, mapping = detect_columns(df)

        if ok:
            st.success(info)
            with st.expander("👀 Preview (first 5 rows)", expanded=True):
                st.dataframe(df.head(5), use_container_width=True)
                st.caption(f"Total rows: **{len(df)}**")

            if st.button("📥 Load Contacts", type="primary", use_container_width=True):
                custs = process_excel(df, mapping)
                if custs:
                    st.session_state["customers"] = custs
                    st.success(f"✅ Loaded **{len(custs)}** contacts!")
                    time.sleep(1); st.rerun()
                else:
                    st.error("❌ No valid contacts found.")
        else:
            st.error(info)

    except ImportError:
        st.error("❌ Missing `openpyxl`. Add it to requirements.txt")
    except Exception as e:
        st.error(f"❌ File error: {e}")

# ── DASHBOARD ─────────────────────────────────────────
if st.session_state["customers"]:
    custs = st.session_state["customers"]
    total, sent, per_hr, per_day, pending = get_stats(custs)

    # Metrics
    st.subheader("📊 Campaign Stats")
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("👥 Total",    total)
    m2.metric("✅ Sent",     sent)
    m3.metric("⏳ Pending",  pending)
    m4.metric("⏱️ This Hour", f"{per_hr}/{max_hr}")
    m5.metric("📅 Today",    f"{per_day}/{max_day}")

    if total:
        st.progress(sent/total, text=f"Progress: {sent}/{total} ({sent/total*100:.1f}%)")

    st.divider()

    # Controls
    c1, c2, c3 = st.columns([0.4, 0.3, 0.3])
    with c1:
        if not st.session_state["sending_active"]:
            if st.button("▶️ START AUTO SENDING", type="primary", use_container_width=True):
                if not gmail_user:
                    st.error("❌ Gmail credentials missing in your profile.")
                else:
                    st.session_state["sending_active"] = True
                    st.rerun()
        else:
            st.success("🟢 Sending Active...")
    with c2:
        if st.session_state["sending_active"]:
            if st.button("⏸️ Pause", use_container_width=True):
                st.session_state["sending_active"] = False; st.rerun()
    with c3:
        if st.button("🔄 Reset Sent", use_container_width=True):
            for c in custs:
                c.update({"whatsapp_sent":False,"email_sent":False,"sent_at":None,"error":None})
            st.session_state["sending_active"] = False; st.rerun()

    # ── SEND LOOP ──────────────────────────────────────
    if st.session_state["sending_active"]:
        if per_hr  >= max_hr:
            st.session_state["sending_active"] = False
            st.warning(f"⚠️ Hourly limit ({max_hr}) reached. Paused."); st.rerun()
        if per_day >= max_day:
            st.session_state["sending_active"] = False
            st.warning(f"⚠️ Daily limit ({max_day}) reached. Paused."); st.rerun()

        do_wa    = "WhatsApp" in send_mode or "Both" in send_mode
        do_email = "Email"    in send_mode or "Both" in send_mode

        nxt = next((
            c for c in custs
            if (do_wa    and c["mobile"] and not c["whatsapp_sent"])
            or (do_email and c["email"]  and not c["email_sent"])
        ), None)

        if nxt:
            st.info(f"📤 Sending to **{nxt['name']}**...")

            if do_wa and nxt["mobile"] and not nxt["whatsapp_sent"]:
                msg = humanize_whatsapp(wa_template, nxt["name"], sender_name) if do_vary \
                      else wa_template.replace("{{name}}", nxt["name"])
                ok, resp = send_whatsapp(nxt["mobile"], msg)
                nxt["whatsapp_sent"] = ok
                if not ok: nxt["error"] = resp; st.warning(resp)

            if do_email and nxt["email"] and not nxt["email_sent"]:
                if do_vary:
                    subj, body = humanize_email(em_body, nxt["name"], em_subject, sender_name)
                else:
                    subj = em_subject.replace("{{name}}", nxt["name"])
                    body = em_body.replace("{{name}}", nxt["name"])
                ok, resp = send_email_smtp(nxt["email"], subj, body, gmail_user, gmail_pass, sender_name)
                nxt["email_sent"] = ok
                if not ok: nxt["error"] = resp; st.warning(resp)

            if nxt["whatsapp_sent"] or nxt["email_sent"]:
                nxt["sent_at"] = datetime.now()

            delay = random.randint(HUMAN_DELAY_MIN, HUMAN_DELAY_MAX)
            with st.spinner(f"⏳ Waiting {delay}s (human delay)..."):
                time.sleep(delay)
            st.rerun()

        else:
            st.session_state["sending_active"] = False
            st.success("🎉 All messages sent!")
            st.balloons(); st.rerun()

    # ── CONTACT TABLE ──────────────────────────────────
    st.divider()
    st.subheader("📋 Contacts")

    fa, fb = st.columns(2)
    with fa:
        filt = st.selectbox("Filter:", ["All","✅ Sent","⏳ Pending","❌ Failed"])
    with fb:
        srch = st.text_input("🔍 Search:", placeholder="name / email / phone")

    shown = custs
    if filt == "✅ Sent":    shown = [c for c in custs if c["whatsapp_sent"] or c["email_sent"]]
    elif filt == "⏳ Pending": shown = [c for c in custs if not c["whatsapp_sent"] and not c["email_sent"]]
    elif filt == "❌ Failed":  shown = [c for c in custs if c.get("error")]

    if srch:
        sl = srch.lower()
        shown = [c for c in shown if sl in c["name"].lower()
                 or sl in c["email"].lower() or sl in c["mobile"]]

    table = [{
        "Name"    : c["name"],
        "Mobile"  : c["mobile"] or "—",
        "Email"   : c["email"]  or "—",
        "WhatsApp": "✅" if c["whatsapp_sent"] else "⏳",
        "Email"   : "✅" if c["email_sent"]    else "⏳",
        "Sent At" : c["sent_at"].strftime("%H:%M:%S") if c.get("sent_at") else "—",
        "Error"   : c.get("error") or "—",
    } for c in shown[:100]]

    if table:
        st.dataframe(pd.DataFrame(table), use_container_width=True, height=380)
        if len(shown) > 100:
            st.caption(f"Showing 100 of {len(shown)}")
    else:
        st.info("No matching contacts.")

    # Export
    if sent > 0:
        export = pd.DataFrame([{
            "Name"        : c["name"],
            "Mobile"      : c["mobile"],
            "Email"       : c["email"],
            "WA Sent"     : c["whatsapp_sent"],
            "Email Sent"  : c["email_sent"],
            "Sent At"     : str(c.get("sent_at") or ""),
            "Error"       : c.get("error") or ""
        } for c in custs])

        st.download_button(
            "📥 Export Results CSV",
            data=export.to_csv(index=False).encode(),
            file_name=f"MarketAI_Results_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    st.markdown("""
    <div style='text-align:center;padding:60px;color:#888'>
        <h2>📁 No Contacts Loaded Yet</h2>
        <p>Upload an Excel or CSV file from the sidebar to get started.</p>
        <p>Download the sample template to see the expected format.</p>
    </div>
    """, unsafe_allow_html=True)
