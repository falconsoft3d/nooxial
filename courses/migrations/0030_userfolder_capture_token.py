from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0029_usercad'),
    ]

    operations = [
        migrations.AddField(
            model_name='userfolder',
            name='capture_token',
            field=models.UUIDField(blank=True, null=True, unique=True, verbose_name='Token de captura'),
        ),
    ]
