from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_company_phone_public_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='pin_hash',
            field=models.CharField(blank=True, max_length=128, verbose_name='PIN de bloqueo (hash)'),
        ),
    ]
