from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_siteconfig_email_passwordresettoken'),
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nombre')),
                ('email', models.EmailField(blank=True, verbose_name='Correo electrónico')),
                ('web', models.URLField(blank=True, verbose_name='Sitio web')),
                ('address', models.CharField(blank=True, max_length=255, verbose_name='Dirección')),
                ('nif', models.CharField(blank=True, max_length=50, verbose_name='NIF / CIF')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Empresa',
                'verbose_name_plural': 'Empresas',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='userprofile',
            name='company',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='users',
                to='accounts.company',
                verbose_name='Empresa',
            ),
        ),
    ]
