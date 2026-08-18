from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0030_userfolder_capture_token'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nombre')),
                ('url', models.URLField(max_length=2000, verbose_name='URL')),
                ('link_user', models.CharField(blank=True, max_length=200, verbose_name='Usuario')),
                ('link_pass', models.CharField(blank=True, max_length=500, verbose_name='Contraseña')),
                ('is_public', models.BooleanField(default=True, verbose_name='Pública')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_links', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Enlace guardado',
                'verbose_name_plural': 'Enlaces guardados',
                'ordering': ['-created_at'],
            },
        ),
    ]
