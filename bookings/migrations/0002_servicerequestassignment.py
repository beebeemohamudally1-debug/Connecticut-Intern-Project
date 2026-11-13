import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('bookings', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='ServiceRequestAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('sent', 'Sent'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn')], default='sent', max_length=10)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('response_note', models.TextField(blank=True)),
                ('handyman', models.ForeignKey(limit_choices_to={'role': 'handyman'}, on_delete=django.db.models.deletion.PROTECT, related_name='service_request_assignments', to=settings.AUTH_USER_MODEL)),
                ('sent_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='service_requests_sent', to=settings.AUTH_USER_MODEL)),
                ('service_request', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='handyman_responses', to='bookings.servicerequest')),
            ],
            options={
                'ordering': ['-sent_at'],
                'constraints': [models.UniqueConstraint(fields=('service_request', 'handyman'), name='one_handyman_offer_per_request')],
            },
        )
    ]
