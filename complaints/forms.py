from django import forms

from jobs.forms import InMixin
from .models import Complaint, ComplaintEvidence


class ComplaintForm(InMixin, forms.ModelForm):
    evidence = forms.FileField(
        required=False, label='Photo or document (JPG, PNG or PDF, max 5 MB)')

    class Meta:
        model = Complaint
        fields = ['job', 'subject', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, user, jobs, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['job'].queryset = jobs
        self.fields['job'].label_from_instance = lambda j: f'{j.reference} · {j.service_name}'

    def clean_evidence(self):
        f = self.cleaned_data.get('evidence')
        if f:
            ComplaintEvidence._meta.get_field('file').run_validators(f)
        return f


class ReplyForm(InMixin, forms.Form):
    body = forms.CharField(label='Your response', widget=forms.Textarea(attrs={'rows': 4}))
    evidence = forms.FileField(required=False, label='Photo or document (JPG, PNG or PDF, max 5 MB)')

    def clean_evidence(self):
        f = self.cleaned_data.get('evidence')
        if f:
            ComplaintEvidence._meta.get_field('file').run_validators(f)
        return f


class EnquiryForm(InMixin, forms.Form):
    recipient = forms.ChoiceField(label='Ask')
    body = forms.CharField(label='Question or request', widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, complaint, **kwargs):
        super().__init__(*args, **kwargs)
        self.complaint = complaint
        people = [complaint.submitted_by] + ([complaint.against] if complaint.against else [])
        self.people = {str(u.pk): u for u in people}
        self.fields['recipient'].choices = [
            (str(u.pk), f'{u.get_full_name() or u.username} ({u.role})') for u in people]

    def clean_recipient(self):
        return self.people[self.cleaned_data['recipient']]


class ResolutionForm(InMixin, forms.Form):
    status = forms.ChoiceField(
        choices=[(Complaint.IN_PROGRESS, 'In progress'), (Complaint.RESOLVED, 'Resolved')])
    outcome = forms.CharField(
        required=False, label='Investigation outcome',
        widget=forms.Textarea(attrs={'rows': 3}))

    def clean(self):
        data = super().clean()
        if data.get('status') == Complaint.RESOLVED and not (data.get('outcome') or '').strip():
            self.add_error('outcome', 'Record the outcome before marking the complaint resolved.')
        return data
