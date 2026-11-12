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
