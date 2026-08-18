from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0023_app_version'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='nav_more_expanded',
            field=models.BooleanField(default=False, verbose_name='Menú expandido'),
        ),
    ]
