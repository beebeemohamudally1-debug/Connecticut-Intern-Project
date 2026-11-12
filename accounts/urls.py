from django.urls import path

# Frontend stubs for now. When the backend views exist, change this one line to:  from . import views as v
from . import frontend_stubs as v

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
    path("preview", v.preview_index, name="preview"),
]
