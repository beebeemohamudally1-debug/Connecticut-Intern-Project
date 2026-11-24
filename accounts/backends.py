from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Checks the password for an email login.

    It deliberately does not reject inactive users, so the login view can say
    'suspended' or 'disabled' only after the password is correct (the front-end
    README asks for this). get_user() is inherited, so a disabled user can never
    keep a session open.
    """

    def authenticate(self, request, email=None, password=None, **kwargs):
        if not email or not password:
            return None
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email.strip())
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            User().set_password(password)   # keep the timing similar either way
            return None
        return user if user.check_password(password) else None