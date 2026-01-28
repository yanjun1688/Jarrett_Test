# Generated migration to remove deprecated models and fields

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('test_ui_app', '0004_convert_to_actions'),
    ]

    operations = [
        # 删除UITestStepExecution模型（因为它依赖于UITestStep）
        migrations.DeleteModel(
            name='UITestStepExecution',
        ),
        # 删除UITestStep模型
        migrations.DeleteModel(
            name='UITestStep',
        ),
        # 删除ElementLocator模型
        migrations.DeleteModel(
            name='ElementLocator',
        ),
        # 删除UITestScript的废弃字段
        migrations.RemoveField(
            model_name='uitestscript',
            name='script_type',
        ),
        migrations.RemoveField(
            model_name='uitestscript',
            name='script_code',
        ),
    ]
