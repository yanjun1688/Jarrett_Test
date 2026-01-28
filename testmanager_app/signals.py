"""
用户信号处理模块

自动为新用户分配默认角色
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from testmanager_app.models import Role, UserRole
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def assign_default_role_to_new_user(sender, instance, created, **kwargs):
    """
    当新用户创建时，自动分配默认的 CRUD 角色
    
    注意：
    - superuser（通过createsuperuser创建）不需要分配角色（在权限检查中已特殊处理）
    - 如果用户已经有角色，则不再分配
    - 如果默认角色不存在，会尝试创建
    """
    # 只处理新创建的用户
    if not created:
        return
    
    # superuser 不需要分配角色（在权限检查中已特殊处理）
    if instance.is_superuser:
        logger.debug(f"Superuser {instance.username} does not need role assignment")
        return
    
    # 检查用户是否已经有角色
    if UserRole.objects.filter(user=instance).exists():
        logger.debug(f"User {instance.username} already has roles assigned, skipping default role assignment")
        return
    
    # 获取或创建默认的 CRUD 角色
    default_role, role_created = Role.objects.get_or_create(
        name='普通用户',
        defaults={
            'permission': 'crud',
            'description': '默认用户角色，拥有增删改查权限'
        }
    )
    
    if role_created:
        logger.info(f"Created default role: {default_role.name}")
    
    # 为用户分配默认角色
    user_role, user_role_created = UserRole.objects.get_or_create(
        user=instance,
        role=default_role
    )
    
    if user_role_created:
        logger.info(f"Assigned default role '{default_role.name}' to user '{instance.username}'")
    else:
        logger.debug(f"User {instance.username} already has role {default_role.name}")

