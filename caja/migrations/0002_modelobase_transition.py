import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('caja', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='caja',
            name='activo',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='caja',
            name='creado_en',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='caja',
            name='actualizado_en',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
