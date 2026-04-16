"""
WebSocket认证中间件，支持Token认证
"""
# pyright: reportAttributeAccessIssue=false
import logging
from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from testmanager_app.models import AuthToken

logger = logging.getLogger(__name__)


class TokenAuthMiddleware(BaseMiddleware):  # type: ignore[misc]
    """
    WebSocket Token认证中间件
    
    从query string中提取token并验证用户身份
    支持格式：ws://host/path?token=xxx 或 ws://host/path?token=xxx&other=value
    """
    
    async def __call__(self, scope, receive, send):
        # 只处理WebSocket连接
        if scope["type"] != "websocket":
            return await super().__call__(scope, receive, send)
        
        # 从query string中提取token
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        
        # 尝试从query string获取token
        token_key = None
        if "token" in query_params:
            token_values = query_params["token"]
            if token_values:
                token_key = token_values[0]
        
        # 如果query string中没有token，尝试从headers中获取（Authorization头）
        if not token_key:
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8")
            if auth_header.startswith("Token "):
                token_key = auth_header[6:].strip()
            elif auth_header.startswith("Bearer "):
                token_key = auth_header[7:].strip()
        
        # 验证token并获取用户
        if token_key:
            user = await self.get_user_from_token(token_key)
        else:
            # 如果没有token，尝试使用session认证（向后兼容）
            user = await self.get_user_from_session(scope)
        
        # 将用户信息添加到scope
        scope["user"] = user
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user_from_token(self, token_key):
        """从token获取用户"""
        try:
            token = AuthToken.objects.select_related('user').get(key=token_key)
            
            # 检查token是否过期
            if token.is_expired():
                token.delete()
                return AnonymousUser()
            
            # 更新最后使用时间
            from django.utils import timezone
            token.last_used = timezone.now()
            token.save(update_fields=['last_used'])
            
            # 检查用户是否激活
            if not token.user.is_active:
                return AnonymousUser()
            
            return token.user
            
        except AuthToken.DoesNotExist:
            return AnonymousUser()
        except Exception as e:
            logger.error(f"Token认证失败: {str(e)}", exc_info=True)
            return AnonymousUser()
    
    @database_sync_to_async
    def get_user_from_session(self, scope):
        """从session获取用户（向后兼容）"""
        from django.contrib.sessions.models import Session
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        try:
            session_key = None
            # 从cookies中获取session key
            for header_name, header_value in scope.get("headers", []):
                if header_name == b"cookie":
                    cookies = header_value.decode("utf-8")
                    for cookie in cookies.split("; "):
                        if cookie.startswith("sessionid="):
                            session_key = cookie.split("=", 1)[1]
                            break
            
            if session_key:
                session = Session.objects.get(session_key=session_key)
                user_id = session.get_decoded().get("_auth_user_id")
                if user_id:
                    user = User.objects.get(pk=user_id)
                    return user
        except Exception as e:
            logger.debug(f"Session认证失败: {str(e)}")
        
        return AnonymousUser()


def TokenAuthMiddlewareStack(inner):
    """Token认证中间件栈"""
    return TokenAuthMiddleware(inner)
