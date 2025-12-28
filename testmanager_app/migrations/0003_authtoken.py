# Generated migration for AuthToken model
# Run: python manage.py makemigrations testmanager_app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('testmanager_app', '0002_alter_requestcollection_project'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthToken',
            fields=[
                ('key', models.CharField(max_length=100, primary_key=True, serialize=False, verbose_name='Token密钥')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('expires_at', models.DateTimeField(verbose_name='过期时间')),
                ('last_used', models.DateTimeField(auto_now=True, verbose_name='最后使用时间')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auth_tokens', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '认证Token',
                'verbose_name_plural': '认证Token',
                'ordering': ['-created'],
            },
        ),
    ]

