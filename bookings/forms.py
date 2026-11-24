from django import forms
from django.utils import timezone

from accounts.models import User
from .models import ServiceRequest


class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = (
            'service_category', 'problem_description', 'service_address',
            'contact_name', 'contact_phone', 'contact_email',
            'preferred_date', 'preferred_slot', 'chosen_handyman',
        )
        widgets = {
            'problem_description': forms.Textarea(attrs={'rows': 5}),
            'preferred_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {'chosen_handyman': 'Choose a handyman'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service_category'].required = True
        self.fields['problem_description'].required = True
        self.fields['service_address'].required = True
        self.fields['contact_name'].required = True
        self.fields['contact_phone'].required = True
        self.fields['chosen_handyman'].queryset = User.objects.filter(
            role='handyman', is_active=True,
        ).order_by('first_name', 'last_name', 'username')
        self.fields['chosen_handyman'].required = True
        self.fields['preferred_date'].required = False
        self.fields['preferred_slot'].required = False

    def clean_preferred_date(self):
        value = self.cleaned_data.get('preferred_date')
        if value and value < timezone.localdate():
            raise forms.ValidationError('Choose today or a future preferred date.')
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('preferred_slot') and not cleaned.get('preferred_date'):
            self.add_error('preferred_date', 'Choose a date before selecting a preferred time slot.')
        return cleaned
