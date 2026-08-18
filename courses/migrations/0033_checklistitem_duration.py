from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0032_checklist'),
    ]

    operations = [
        migrations.AddField(
            model_name='checklistitem',
            name='duration',
            field=models.PositiveSmallIntegerField(default=1, verbose_name='Duración (unidades)'),
        ),
    ]
