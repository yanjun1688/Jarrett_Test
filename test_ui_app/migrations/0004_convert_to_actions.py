# Generated migration to convert existing code/steps to actions

from django.db import migrations, models


def convert_code_to_actions(apps, schema_editor):
    """将code模式的脚本转换为actions"""
    UITestScript = apps.get_model('test_ui_app', 'UITestScript')
    
    # 动态导入（迁移中不能直接导入应用代码）
    import sys
    import os
    
    # 添加项目路径到sys.path
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # 注意：CodeParser已被删除，代码模式不再支持
    # 如果存在code模式的脚本，将它们标记为需要手动转换
    try:
        scripts = UITestScript.objects.filter(script_type='code').exclude(script_code='')
        if scripts.exists():
            print(f"[WARN] 发现 {scripts.count()} 个code模式的脚本，但这些脚本无法自动转换（CodeParser已删除）")
            print(f"[WARN] 建议手动将这些脚本转换为actions格式")
            # 不抛出异常，继续执行迁移
    except Exception as e:
        print(f"[WARN] 检查code模式脚本时出错: {str(e)}")
        # 继续执行迁移


def convert_steps_to_actions(apps, schema_editor):
    """将steps模式的脚本转换为actions"""
    UITestScript = apps.get_model('test_ui_app', 'UITestScript')
    
    # 检查UITestStep模型是否还存在（在0005迁移中会被删除）
    try:
        UITestStep = apps.get_model('test_ui_app', 'UITestStep')
    except LookupError:
        # 模型已不存在（可能在0005迁移后运行此迁移）
        print("[WARN] UITestStep模型不存在，跳过steps转换")
        return
    
    # 动态导入
    import sys
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    try:
        from test_ui_app.converters.action_converter import StepsToActionsConverter
        
        converter = StepsToActionsConverter()
        scripts = UITestScript.objects.filter(script_type='steps')
        
        for script in scripts:
            try:
                # 获取所有步骤
                steps = list(
                    UITestStep.objects.filter(script=script, is_enabled=True)
                    .select_related('element_locator')
                    .order_by('step_order')
                )
                
                if steps:
                    # 转换为字典格式
                    steps_data = []
                    for step in steps:
                        step_dict = {
                            'action_type': step.action_type,
                            'action_params': step.action_params or {},
                            'description': step.description or '',
                            'is_enabled': step.is_enabled,
                        }
                        if step.element_locator:
                            step_dict['element_locator'] = {
                                'locator_type': step.element_locator.locator_type,
                                'locator_value': step.element_locator.locator_value,
                            }
                        steps_data.append(step_dict)
                    
                    # 转换为actions
                    actions = converter.convert(steps_data)
                    script.actions = actions
                    script.save(update_fields=['actions'])
                    print(f"转换脚本 {script.id} (steps模式): {len(actions)} 个actions")
                    
            except Exception as e:
                print(f"转换脚本 {script.id} 失败: {str(e)}")
                # 继续处理其他脚本
                
    except ImportError as e:
        print(f"无法导入StepsToActionsConverter: {str(e)}")


def reverse_migration(apps, schema_editor):
    """反向迁移（清空actions字段）"""
    UITestScript = apps.get_model('test_ui_app', 'UITestScript')
    UITestScript.objects.all().update(actions=[])


class Migration(migrations.Migration):

    dependencies = [
        ('test_ui_app', '0003_add_script_type_and_script_code'),
    ]

    operations = [
        # 首先添加actions字段（使用空列表作为默认值）
        migrations.AddField(
            model_name='uitestscript',
            name='actions',
            field=models.JSONField(default=list, verbose_name='动作列表'),
            preserve_default=True,
        ),
        # 修改script_type和script_code字段为可空（用于向后兼容）
        migrations.AlterField(
            model_name='uitestscript',
            name='script_type',
            field=models.CharField(
                blank=True,
                choices=[('code', '代码模式'), ('steps', '步骤模式')],
                default='steps',
                help_text='已废弃，保留用于数据迁移兼容',
                max_length=20,
                null=True,
                verbose_name='脚本类型',
            ),
        ),
        migrations.AlterField(
            model_name='uitestscript',
            name='script_code',
            field=models.TextField(
                blank=True,
                help_text='已废弃，保留用于数据迁移兼容',
                null=True,
                verbose_name='脚本代码',
            ),
        ),
        # 运行数据转换
        migrations.RunPython(
            convert_code_to_actions,
            reverse_migration,
        ),
        migrations.RunPython(
            convert_steps_to_actions,
            reverse_migration,
        ),
    ]

