from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0027_presentation_share'),
    ]

    operations = [
        migrations.AddField(
            model_name='userfolder',
            name='shared_with_all',
            field=models.BooleanField(default=False, verbose_name='Compartida con todos'),
        ),
    ]
