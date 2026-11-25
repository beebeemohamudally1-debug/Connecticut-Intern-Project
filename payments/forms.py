from django import forms

from .models import (InvoicePayment, LabourEstimate, MaterialPurchaseRequest, MaterialReceipt, Payment, Quotation,
                     default_due_date, default_payment_instructions)


class StyledMixin:
    """Adds the 'in' CSS class from style.css to every field."""

    def style_fields(self):
        for field in self.fields.values():
            field.widget.attrs['class'] = 'in'


class StyledModelForm(StyledMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()


class NoteForm(StyledMixin, forms.Form):
    note = forms.CharField(label='Note', widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()


class QuotationForm(StyledModelForm):
    class Meta:
        model = Quotation
        fields = ['work_description', 'total_amount']
        labels = {'work_description': 'Work included', 'total_amount': 'Fixed total (MUR)'}
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


class LabourEstimateForm(StyledModelForm):
    class Meta:
        model = LabourEstimate
        fields = ['amount', 'breakdown']
        labels = {'amount': 'Labour estimate (MUR)', 'breakdown': 'Breakdown of the work'}
        widgets = {'breakdown': forms.Textarea(attrs={'rows': 4})}


class MaterialRequestForm(StyledModelForm):
    class Meta:
        model = MaterialPurchaseRequest
        fields = ['items', 'estimated_cost']
        labels = {'items': 'Materials to buy', 'estimated_cost': 'Estimated cost (MUR)'}
        widgets = {'items': forms.Textarea(attrs={'rows': 4})}


class MaterialReceiptForm(StyledModelForm):
    class Meta:
        model = MaterialReceipt
        fields = ['image', 'amount_spent']
        labels = {'image': 'Receipt photo', 'amount_spent': 'Amount spent (MUR)'}


# ---------------------------------------------------------- invoices
def _date_widget():
    return forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')


class InvoiceIssueForm(StyledMixin, forms.Form):
    """Admin: issue a job invoice. The amounts come from the accepted quotations."""

    due_date = forms.DateField(label='Payment deadline', widget=_date_widget(), initial=default_due_date)
    payment_instructions = forms.CharField(label='Payment instructions', widget=forms.Textarea(attrs={'rows': 3}),
                                           initial=default_payment_instructions)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()


class InspectionInvoiceForm(StyledMixin, forms.Form):
    """Admin: issue the fixed inspection fee. The fee itself is set in settings, not typed in."""

    reason = forms.CharField(label='Reason given by handyman', widget=forms.Textarea(attrs={'rows': 3}))
    due_date = forms.DateField(label='Payment deadline', widget=_date_widget(), initial=default_due_date)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()


class InvoicePaymentForm(StyledModelForm):
    received = forms.ChoiceField(label='Payment status', choices=[('yes', 'Received'), ('no', 'Not received')])

    class Meta:
        model = InvoicePayment
        fields = ['amount', 'date_received', 'method', 'reference']
        labels = {
            'amount': 'Amount received (MUR)',
            'date_received': 'Date received',
            'method': 'Payment method',
            'reference': 'Reference number (optional)',
        }
        widgets = {'date_received': _date_widget()}
