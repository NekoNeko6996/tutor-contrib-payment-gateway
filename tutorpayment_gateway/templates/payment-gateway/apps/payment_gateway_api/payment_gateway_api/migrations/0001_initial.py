from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import uuid

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('uid', models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
                ('course_id', models.CharField(max_length=255)),
                ('mode', models.CharField(max_length=32, default='verified')),
                ('amount', models.DecimalField(max_digits=12, decimal_places=2)),
                ('currency', models.CharField(max_length=8, default='VND')),
                ('status', models.CharField(max_length=16, choices=[
                    ('PENDING','PENDING'),('PAID','PAID'),('FAILED','FAILED'),('CANCELED','CANCELED')
                ], default='PENDING')),
                ('provider', models.CharField(max_length=32, blank=True)),
                ('external_txn_id', models.CharField(max_length=128, blank=True)),
                ('idempotency_key', models.CharField(max_length=64, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['uid','status','course_id'], name='order_uid_status_course_idx'),
        ),
    ]
