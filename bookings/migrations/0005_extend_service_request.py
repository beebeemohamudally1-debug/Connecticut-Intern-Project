import django.utils.timezone
from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


def populate_references(apps, schema_editor):
    ServiceRequest = apps.get_model('bookings', 'ServiceRequest')
    for request in ServiceRequest.objects.filter(reference__isnull=True) | ServiceRequest.objects.filter(reference=''):
        request.reference = f'SR-{1000 + request.pk}'
        request.save(update_fields=['reference'])


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_handymanprofilerequest'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='servicerequest', options={'ordering': ['-created_at']},
        ),
        migrations.AlterField(
            model_name='servicerequest', name='customer',
            field=models.ForeignKey(
                limit_choices_to={'role': 'customer'}, on_delete=django.db.models.deletion.CASCADE,
                related_name='service_requests', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='servicerequest', name='reference',
            field=models.CharField(blank=True, editable=False, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='servicerequest', name='service_category',
            field=models.CharField(blank=True, max_length=100, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='servicerequest', name='problem_description',
            field=models.TextField(blank=True, default=''), preserve_default=False,
        ),
        migrations.AddField(
            model_name='servicerequest', name='service_address',
            field=models.CharField(blank=True, max_length=255, default=''), preserve_default=False,
        ),
        migrations.AddField(
            model_name='servicerequest', name='contact_name',
            field=models.CharField(blank=True, max_length=100, default=''), preserve_default=False,
        ),
        migrations.AddField(
            model_name='servicerequest', name='contact_phone',
            field=models.CharField(blank=True, max_length=20, default=''), preserve_default=False,
        ),
        migrations.AddField(
            model_name='servicerequest', name='contact_email',
            field=models.EmailField(blank=True, max_length=254, default=''), preserve_default=False,
        ),
        migrations.AddField(
            model_name='servicerequest', name='preferred_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='servicerequest', name='preferred_slot',
            field=models.CharField(blank=True, choices=[('morning', 'Morning'), ('afternoon', 'Afternoon')], max_length=10, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='servicerequest', name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='servicerequest', name='updated_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.RunPython(populate_references, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='servicerequest', name='reference',
            field=models.CharField(blank=True, editable=False, max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name='servicerequest', name='status',
            field=models.CharField(
                choices=[('requested', 'Requested'), ('submitted', 'Submitted'), ('reviewing', 'Under review'), ('assigned', 'Sent to handymen'), ('booked', 'Booked'), ('cancelled', 'Cancelled'), ('completed', 'Completed')],
                default='requested', max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='servicerequest', name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='servicerequest', name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
