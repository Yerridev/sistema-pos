from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='categoria',
            old_name='created_at',
            new_name='creado_en',
        ),
        migrations.RenameField(
            model_name='categoria',
            old_name='updated_at',
            new_name='actualizado_en',
        ),
        migrations.RenameField(
            model_name='producto',
            old_name='created_at',
            new_name='creado_en',
        ),
        migrations.RenameField(
            model_name='producto',
            old_name='updated_at',
            new_name='actualizado_en',
        ),
        migrations.AddConstraint(
            model_name='producto',
            constraint=models.CheckConstraint(
                condition=models.Q(('stock_actual__gte', 0)),
                name='stock_no_negativo',
            ),
        ),
        migrations.AddConstraint(
            model_name='producto',
            constraint=models.CheckConstraint(
                condition=models.Q(('precio_venta__gte', models.F('costo'))),
                name='precio_venta_mayor_igual_costo',
            ),
        ),
    ]
