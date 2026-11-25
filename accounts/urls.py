from django.urls import path

# Frontend stubs for now. When the backend views exist, change this one line to:  from . import views as v
from . import frontend_stubs as v
from . import frontend_stubs_register as r  # registration (S02 to S11); switch to views too
from . import views

app_name = "accounts"

urlpatterns = [
    path("", v.home, name="home"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("forgot-password", views.forgot_password, name="forgot_password"),
    path("forgot-password/verify", views.reset_verify, name="reset_verify"),
    path("forgot-password/new", views.reset_new, name="reset_new"),
    path("forgot-password/done", v.reset_done, name="reset_done"),
    path("provider/status", v.provider_status, name="provider_status"),
    # Admin sign-in lives under admin-portal/ because Django's own admin already owns admin/.
    path("admin-portal/login/mfa", v.admin_mfa, name="admin_mfa"),
    path("admin-portal/first-login", v.admin_first_login, name="admin_first_login"),
    # Registration (S02 to S11)
    path("register", views.register_role, name="register"),
    path("register/email", views.register_email, name="register_email"),
    path("register/confirm-email", views.register_confirm, name="register_confirm"),
    path("register/verify", views.register_verify, name="register_verify"),
    path("register/password", views.register_password, name="register_password"),
    path("register/expired", views.register_expired, name="register_expired"),
    path("register/customer", views.register_customer, name="register_customer"),
    path("register/customer/done", views.register_done, name="register_done"),
    # Service provider registration (S10, S10b, S11)
    path("register/provider", views.register_provider, name="register_provider"),
    path("register/provider/documents", views.register_provider_documents, name="register_provider_documents"),
    path("register/provider/done", views.register_provider_done, name="register_provider_done"),
    path("register/check-username", views.username_check, name="username_check"),
    path("preview", v.preview_index, name="preview"),
]

