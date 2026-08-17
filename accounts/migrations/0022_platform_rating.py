from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0021_userprofile_cv_github'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PlatformRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.CharField(
                    choices=[('happy', '😊 Feliz'), ('neutral', '😐 Neutral'), ('sad', '😞 Triste')],
                    max_length=10, verbose_name='Valoración',
                )),
                ('comment', models.TextField(blank=True, verbose_name='Comentario')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha')),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='platform_ratings',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuario',
                )),
            ],
            options={
                'verbose_name': 'Evaluación de plataforma',
                'verbose_name_plural': 'Evaluaciones de plataforma',
                'ordering': ['-created_at'],
            },
        ),
    ]
