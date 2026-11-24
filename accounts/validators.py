import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import CommonPasswordValidator
from django.core.exceptions import ValidationError
from PIL import Image
from services.models import ServiceArea, ServiceCategory

from . import auth_messages as M

User = get_user_model()


def password_rules(password):
    """[(key, label, met)] for the five password rules shown on the page."""
    try:
        CommonPasswordValidator().validate(password)
        not_common = True
    except ValidationError:
        not_common = False
    met = {
        'len': len(password) >= 8,
        'upper': bool(re.search(r'[A-Z]', password)),
        'lower': bool(re.search(r'[a-z]', password)),
        'digit': bool(re.search(r'\d', password)),
        'common': not_common and bool(password),
    }
    return [(key, label, met[key]) for key, label in M.PW_RULES]


def _name_ok(value):
    return bool(re.fullmatch(r"[^\W\d_][\w' .-]*", value, re.UNICODE)) and not re.search(r'[\d_]', value)


def username_valid(username):
    return bool(re.fullmatch(r'\w{3,30}', username, re.ASCII))


def username_taken(username):
    return User.objects.filter(username__iexact=username).exists()


def validate_customer(values, terms, privacy):
    """Field errors for the customer details form (wording from auth_messages)."""
    e = M.CUSTOMER_ERRORS
    errors = {}
    if not _name_ok(values['first_name']):
        errors['first_name'] = e['first_name']
    if not _name_ok(values['surname']):
        errors['surname'] = e['surname']
    if values['additional_names'] and not _name_ok(values['additional_names']):
        errors['additional_names'] = e['additional_names']
    if not username_valid(values['username']):
        errors['username'] = e['username']
    elif username_taken(values['username']):
        errors['username'] = M.USERNAME_TAKEN
    if not re.fullmatch(r'\d{8}', values['phone'], re.ASCII):
        errors['phone'] = e['phone']
    if not ServiceArea.objects.filter(name=values['region'], is_active=True).exists():
        errors['region'] = e['region']
    if not values['address']:
        errors['address'] = e['address']
    if not terms:
        errors['terms'] = e['terms']
    if not privacy:
        errors['privacy'] = e['privacy']
    return errors

DOC_FORMATS = {'JPEG': '.jpg', 'PNG': '.png'}


def check_image(f):
    """Return (error message, file extension). Checks the size and the real content."""
    if f.size > M.DOC_MAX_MB * 1024 * 1024:
        return f'{f.name}: {M.FILE_SIZE_ERROR}', ''
    try:
        f.seek(0)
        with Image.open(f) as img:
            img.verify()
            image_format = img.format
    except Exception:
        return f'{f.name}: {M.FILE_TYPE_ERROR}', ''
    f.seek(0)
    if image_format not in DOC_FORMATS:
        return f'{f.name}: {M.FILE_TYPE_ERROR}', ''
    return '', DOC_FORMATS[image_format]


def validate_provider(values, regions, categories):
    """Field errors for the provider details form (S10)."""
    errors = validate_customer({**values, 'region': (regions or [''])[0]}, True, True)
    errors.pop('region', None)   # a provider has regions, not one region
    active_regions = set(ServiceArea.objects.filter(is_active=True).values_list('name', flat=True))
    active_categories = set(ServiceCategory.objects.filter(is_active=True).values_list('name', flat=True))
    if not regions or not set(regions) <= active_regions:
        errors['regions'] = M.PROVIDER_ERRORS['regions']
    if not categories or not set(categories) <= active_categories:
        errors['categories'] = M.PROVIDER_ERRORS['categories']
    return errors


def validate_documents(id_file, certificates, terms, privacy):
    """Errors for the documents form (S10b)."""
    errors = {}
    if id_file is None:
        errors['id_photo'] = M.DOC_ERRORS['id_photo']
    else:
        message, _ = check_image(id_file)
        if message:
            errors['id_photo'] = message
    if not certificates:
        errors['certificates'] = M.DOC_ERRORS['certificates']
    else:
        problems = [m for m, _ in (check_image(c) for c in certificates) if m]
        if problems:
            errors['certificates'] = ' '.join(problems)
    if not terms:
        errors['terms'] = M.DOC_ERRORS['terms']
    if not privacy:
        errors['privacy'] = M.DOC_ERRORS['privacy']
    return errors