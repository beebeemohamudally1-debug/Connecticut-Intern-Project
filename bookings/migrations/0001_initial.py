import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name='ServiceRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(blank=True, editable=False, max_length=20, unique=True)),
                ('service_category', models.CharField(max_length=100)),
                ('problem_description', models.TextField()),
                ('service_address', models.CharField(max_length=255)),
                ('contact_name', models.CharField(max_length=100)),
                ('contact_phone', models.CharField(max_length=20)),
                ('contact_email', models.EmailField(blank=True, max_length=254)),
                ('preferred_date', models.DateField()),
                ('preferred_slot', models.CharField(choices=[('morning', 'Morning'), ('afternoon', 'Afternoon')], max_length=10)),
                ('status', models.CharField(choices=[('submitted', 'Submitted'), ('reviewing', 'Under review'), ('assigned', 'Sent to handymen'), ('booked', 'Booked'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], default='submitted', max_length=20)),
                ('full_payment_received_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(limit_choices_to={'role': 'customer'}, on_delete=django.db.models.deletion.PROTECT, related_name='service_requests', to=settings.AUTH_USER_MODEL)),
                ('payment_recorded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payments_recorded_for_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        )
    ]
