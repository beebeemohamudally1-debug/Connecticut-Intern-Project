from django import forms

from .models import Job, ProgressReport, WorkEvidence


class InMixin:
    """Give inputs the `in` CSS class used by the project stylesheet."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.ClearableFileInput)):
                field.widget.attrs.setdefault('class', 'in')


class ProgressReportForm(InMixin, forms.ModelForm):
    class Meta:
        model = ProgressReport
        fields = ['details', 'percent_complete']
        widgets = {'details': forms.Textarea(attrs={'rows': 4})}
        labels = {'details': 'What was done today?', 'percent_complete': 'Overall progress (%)'}


class EvidenceForm(InMixin, forms.ModelForm):
    class Meta:
        model = WorkEvidence
        fields = ['image', 'caption']
        labels = {'image': 'Photo (JPG or PNG, max 5 MB)'}


class CompletionForm(InMixin, forms.ModelForm):
    class Meta:
        model = Job
        fields = ['completion_notes']
        widgets = {'completion_notes': forms.Textarea(attrs={'rows': 3})}
        labels = {'completion_notes': 'Completion notes'}

    def clean_completion_notes(self):
        notes = self.cleaned_data['completion_notes'].strip()
        if not notes:
            raise forms.ValidationError('Add completion notes before submitting the job.')
        return notes


class FlagForm(InMixin, forms.Form):
    reason = forms.CharField(
        label='Reason for flagging', widget=forms.Textarea(attrs={'rows': 2}))
