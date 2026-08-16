from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_company_userprofile_company'),
    ]

    operations = [
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100, verbose_name='Nombre')),
                ('last_name', models.CharField(blank=True, max_length=100, verbose_name='Apellidos')),
                ('email', models.EmailField(verbose_name='Email')),
                ('phone', models.CharField(blank=True, max_length=30, verbose_name='Teléfono')),
                ('company', models.CharField(blank=True, max_length=200, verbose_name='Empresa')),
                ('position', models.CharField(blank=True, max_length=100, verbose_name='Cargo')),
                ('message', models.TextField(blank=True, verbose_name='Mensaje')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Contacto',
                'verbose_name_plural': 'Contactos',
                'ordering': ['-created_at'],
            },
        ),
    ]
