from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0016_article_comments'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='demo_url',
            field=models.URLField(blank=True, verbose_name='URL de acceso demo'),
        ),
        migrations.AddField(
            model_name='course',
            name='demo_login',
            field=models.CharField(blank=True, max_length=255, verbose_name='Usuario demo'),
        ),
        migrations.AddField(
            model_name='course',
            name='demo_password',
            field=models.CharField(blank=True, max_length=255, verbose_name='Contraseña demo'),
        ),
    ]
