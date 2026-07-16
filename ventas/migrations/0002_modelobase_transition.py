import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='activo',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='venta',
            name='creado_en',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='venta',
            name='actualizado_en',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
