import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_contact'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='phone',
            field=models.CharField(blank=True, max_length=30, verbose_name='Teléfono'),
        ),
        migrations.AddField(
            model_name='company',
            name='public_token',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False,
                                   verbose_name='Token público'),
        ),
    ]
