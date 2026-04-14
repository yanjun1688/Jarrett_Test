"""
自定义认证类，支持token过期检查
"""
from rest_framework import authentication, exceptions
from testmanager_app.models import AuthToken
from django.utils import timezone


class ExpiringTokenAuthentication(authentication.TokenAuthentication):
    """
    支持过期时间的Token认证
    """
    model = AuthToken
    
    def authenticate_credentials(self, key):
        """验证token并检查是否过期"""
        try:
            token = self.model.objects.select_related('user').get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')
        
        if token.is_expired():
            token.delete()
            raise exceptions.AuthenticationFailed('Token has expired.')
        
        token.last_used = timezone.now()
        token.save(update_fields=['last_used'])
        
        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')
        
        return (token.user, token)

