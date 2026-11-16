from django import forms

from .models import LabourEstimate, MaterialPurchaseRequest, MaterialReceipt, Payment, Quotation


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
