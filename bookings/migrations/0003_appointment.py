import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('bookings', '0002_servicerequestassignment')]

    operations = [
        migrations.CreateModel(
            name='Appointment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('appointment_type', models.CharField(choices=[('inspection', 'Inspection visit'), ('service', 'Service appointment')], default='service', max_length=12)),
                ('appointment_date', models.DateField()),
                ('time_slot', models.CharField(choices=[('morning', 'Morning'), ('afternoon', 'Afternoon')], max_length=10)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], default='pending', max_length=10)),
                ('notes', models.TextField(blank=True)),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('confirmed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='appointments_confirmed', to=settings.AUTH_USER_MODEL)),
                ('handyman', models.ForeignKey(limit_choices_to={'role': 'handyman'}, on_delete=django.db.models.deletion.PROTECT, related_name='appointments', to=settings.AUTH_USER_MODEL)),
                ('service_request', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='appointments', to='bookings.servicerequest')),
            ],
            options={
                'ordering': ['appointment_date', 'time_slot'],
                'constraints': [models.UniqueConstraint(condition=models.Q(('status', 'confirmed')), fields=('handyman', 'appointment_date', 'time_slot'), name='no_overlapping_confirmed_handyman_slots')],
            },
        )
    ]
