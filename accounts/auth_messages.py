"""All user-facing copy for the login and password-recovery pages, quoted from the lo-fi frames.

Views import this module instead of retyping text, so the wording cannot drift from the design.
"""
LOGIN_SUBTITLE = "Enter your email and password to access your account."
EMAIL_REQUIRED = "Enter your email address."
PASSWORD_REQUIRED = "Enter your password."
INVALID_CREDENTIALS = "Invalid email or password"
LOCKED = "Your account is locked for 15 minutes after 5 failed login attempts. Please try again later."
SUSPENDED = "Your account has been suspended."
DISABLED = "Your account has been disabled."
REJECTED = "Your account has been rejected. {reason}"
FORGOT_SUBTITLE = "Enter your email address to request a password reset code."
FORGOT_GENERIC = "If an account exists, we have sent instructions."
CODE_WRONG = "Incorrect code. Please try again."
CODE_EXPIRED = "This code has expired. Request a new code."
CODE_LOCKED = "Verification locked after 3 failed attempts. Request a new code."
CODE_HOURLY = "You can request up to 5 codes per hour. The hourly resend limit has been reached."
CODE_COOLDOWN = "Please wait before requesting another code."
RESET_RULES_UNMET = "Your password does not meet all requirements."
RESET_MISMATCH = "Passwords do not match."
RESET_DONE = "Password changed. All other sessions were signed out."
PW_RULES = [
    ("len", "8+ characters"),
    ("upper", "At least one uppercase letter"),
    ("lower", "At least one lowercase letter"),
    ("digit", "At least one number"),
    ("common", "Not a common password"),
]
ADMIN_CODE_WRONG = "Incorrect code. Enter the current code from your authenticator app."

# ---------------------------------------------------------------------------
# Registration (S02 to S09). Quoted from the lo-fi frames; the few lines marked NEW
# are not in the design (it names the state but gives no text) and are recorded in the README.
# ---------------------------------------------------------------------------
ROLE_CUSTOMER = "Customer"
ROLE_PROVIDER = "Service Provider"
ROLE_REQUIRED = "Select an account type to continue."  # NEW
REG_EMAIL_INVALID = "Enter a valid email address."  # NEW
REG_EMAIL_TAKEN = "This email address is already registered."  # NEW
REG_CONFIRM_HINT = "Check that your email address is correct before requesting a code."
REG_CODE_WRONG = "Incorrect code. Please try again."
REG_CODE_EXPIRED = "Your code has expired. Request a new code."
REG_CODE_LOCKED = "Locked after 3 failed attempts. Request a new code to continue."
REG_CODE_HOURLY = "Resend limit reached: 5 codes per hour. Please try again later."
REG_CODE_SENT = "A new code has been sent. Any earlier code no longer works."  # NEW
REG_PW_UNMET = "Your password does not meet all requirements."
REG_PW_MISMATCH = "Passwords do not match."
REG_SESSION_EXPIRED = "Your registration session has expired. For your security, please start again."  # NEW

USERNAME_TAKEN = "This username is already taken."
USERNAME_FREE = "Username is available."  # NEW
CUSTOMER_ERRORS = {
    "first_name": "Enter a valid first name.",
    "surname": "Enter a valid surname.",
    "additional_names": "Enter valid additional names, or leave this optional field blank.",
    "username": "Use 3-30 characters: letters, digits and underscores.",
    "phone": "Enter a phone number with exactly 8 digits.",
    "region": "Select your region.",
    "address": "Enter your residential address.",
    "terms": "You must accept the Terms and Conditions.",
    "privacy": "You must accept the Privacy Policy.",
}
# The nine regions of the residential-region dropdown (value, label). Backend: load these from the Region model.
REGIONS = [
    (name, name) for name in (
        "Port Louis", "Pamplemousses", "Riviere du Rempart", "Flacq", "Grand Port",
        "Savanne", "Plaines Wilhems", "Moka", "Black River",
    )
]
