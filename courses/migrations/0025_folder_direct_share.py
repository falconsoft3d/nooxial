from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0022_platform_rating'),
        ('courses', '0024_slug_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FolderShare',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('folder', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='direct_shares',
                    to='courses.userfolder',
                    verbose_name='Carpeta',
                )),
                ('shared_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='folders_shared_out',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Compartido por',
                )),
                ('with_user', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='folders_shared_in',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Con usuario',
                )),
                ('with_company', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='shared_folders',
                    to='accounts.company',
                    verbose_name='Con empresa',
                )),
            ],
            options={
                'verbose_name': 'Carpeta compartida',
                'verbose_name_plural': 'Carpetas compartidas',
                'ordering': ['-created_at'],
            },
        ),
    ]
