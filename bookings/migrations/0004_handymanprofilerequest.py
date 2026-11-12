import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('bookings', '0003_appointment')]

    operations = [
        migrations.CreateModel(
            name='HandymanProfileRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_type', models.CharField(choices=[('service', 'Service'), ('skill', 'Skill')], max_length=10)),
                ('action', models.CharField(choices=[('add', 'Add'), ('modify', 'Modify'), ('remove', 'Remove')], max_length=10)),
                ('current_value', models.CharField(blank=True, max_length=120)),
                ('requested_value', models.CharField(blank=True, max_length=120)),
                ('reason', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('admin_note', models.TextField(blank=True)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('handyman', models.ForeignKey(limit_choices_to={'role': 'handyman'}, on_delete=django.db.models.deletion.PROTECT, related_name='profile_change_requests', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='handyman_profile_requests_reviewed', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['status', '-submitted_at'],
            },
        )
    ]
