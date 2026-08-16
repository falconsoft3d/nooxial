import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_site_config'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Nuevos campos de email en SiteConfig
        migrations.AddField(
            model_name='siteconfig',
            name='email_host',
            field=models.CharField(blank=True, default='smtp.gmail.com', max_length=255, verbose_name='Servidor SMTP'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='email_port',
            field=models.PositiveIntegerField(default=587, verbose_name='Puerto SMTP'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='email_host_user',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Usuario SMTP (email remitente)'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='email_host_password',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Contraseña SMTP'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='email_use_tls',
            field=models.BooleanField(default=True, verbose_name='Usar TLS'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='email_use_ssl',
            field=models.BooleanField(default=False, verbose_name='Usar SSL'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='default_from_email',
            field=models.CharField(blank=True, default='', help_text='Ej: Nooxial <no-reply@tudominio.com>. Si está vacío se usa el usuario SMTP.', max_length=255, verbose_name='Dirección "De" por defecto'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='send_welcome_email',
            field=models.BooleanField(default=False, verbose_name='Enviar email de bienvenida al registrarse'),
        ),
        # Modelo PasswordResetToken
        migrations.CreateModel(
            name='PasswordResetToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('used', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='password_reset_tokens', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Token de recuperación',
                'verbose_name_plural': 'Tokens de recuperación',
            },
        ),
    ]
