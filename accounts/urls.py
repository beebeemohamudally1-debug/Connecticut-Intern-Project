from django.urls import path

# Frontend stubs for now. When the backend views exist, change this one line to:  from . import views as v
from . import frontend_stubs as v
from . import frontend_stubs_register as r  # customer registration (S02 to S09); switch to views too

app_name = "accounts"

urlpatterns = [
    path("", v.home, name="home"),
    path("login", v.login_view, name="login"),
    path("logout", v.logout_view, name="logout"),
    path("forgot-password", v.forgot_password, name="forgot_password"),
    path("forgot-password/verify", v.reset_verify, name="reset_verify"),
    path("forgot-password/new", v.reset_new, name="reset_new"),
    path("forgot-password/done", v.reset_done, name="reset_done"),
    path("provider/status", v.provider_status, name="provider_status"),
    # Admin sign-in lives under admin-portal/ because Django's own admin already owns admin/.
    path("admin-portal/login/mfa", v.admin_mfa, name="admin_mfa"),
    path("admin-portal/first-login", v.admin_first_login, name="admin_first_login"),
    # Registration (S02 to S09)
    path("register", r.register_role, name="register"),
    path("register/email", r.register_email, name="register_email"),
    path("register/confirm-email", r.register_confirm, name="register_confirm"),
    path("register/verify", r.register_verify, name="register_verify"),
    path("register/password", r.register_password, name="register_password"),
    path("register/expired", r.register_expired, name="register_expired"),
    path("register/customer", r.register_customer, name="register_customer"),
    path("register/customer/done", r.register_done, name="register_done"),
    path("register/check-username", r.username_check, name="username_check"),
    path("preview", v.preview_index, name="preview"),
]
