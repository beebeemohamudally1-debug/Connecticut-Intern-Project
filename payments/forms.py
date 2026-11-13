from django import forms

from .models import Payment, Quotation


class StyledModelForm(forms.ModelForm):
    """Adds the 'in' CSS class from style.css to every field."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'in'


class QuotationForm(StyledModelForm):
    class Meta:
        model = Quotation
        fields = ['work_description', 'total_amount']
        labels = {
            'work_description': 'Work included',
            'total_amount': 'Fixed total (MUR)',
        }
        widgets = {'work_description': forms.Textarea(attrs={'rows': 4})}


class PaymentForm(StyledModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'date_received', 'method', 'reference']
        labels = {
            'amount': 'Amount received (MUR)',
            'date_received': 'Date received',
            'method': 'Payment method',
            'reference': 'Reference number (optional)',
        }
        widgets = {'date_received': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}
