from django import forms

from services.models import Service, ServiceCategory


class ServiceForm(forms.ModelForm):

    category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.filter(
            is_active=True
        ).order_by('name'),
        required=True,
    )

    description = forms.CharField(
        required=True,
        widget=forms.Textarea,
    )

    availability = forms.ChoiceField(
        choices=[
            ('active', 'Available'),
            ('inactive', 'Unavailable'),
        ],
        required=True,
    )

    class Meta:
        model = Service
        fields = ['name', 'category', 'description', 'image']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields['category'].queryset = (
                ServiceCategory.objects.filter(
                    is_active=True
                ) | ServiceCategory.objects.filter(
                    pk=self.instance.category_id
                )
            ).order_by('name')

    def clean_image(self):
        image = self.cleaned_data.get('image')

        if image and 'image' in self.changed_data:
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    'Image size must not exceed 5 MB.'
                )

            if image.image.format not in ('JPEG', 'PNG', 'WEBP'):
                raise forms.ValidationError(
                    'Only JPG, PNG and WEBP images are allowed.'
                )

        return image

    def clean(self):
        cleaned_data = super().clean()

        name = cleaned_data.get('name')
        category = cleaned_data.get('category')

        if name and category:
            existing = Service.objects.filter(
                name__iexact=name,
                category=category,
            ).exclude(pk=self.instance.pk)

            if existing.exists():
                self.add_error(
                    'name',
                    'This service already exists in this category.'
                )

        return cleaned_data

    def save(self, commit=True):
        service = super().save(commit=False)

        service.is_active = (
            self.cleaned_data['availability'] == 'active'
        )

        if commit:
            service.save()

        return service
