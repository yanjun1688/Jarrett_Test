"""
用户管理视图和认证相关视图
包含：UserViewSet, FeatureTestCaseViewSet
以及认证相关视图：LoginView, MeView, LogoutView
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from rest_framework.request import Request

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.authentication import BaseAuthentication
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta

from testmanager_app.models import FeatureTestCase, AuthToken
from testmanager_app.serializers import (
    UserListSerializer,
    FeatureTestCaseSerializer
)
from testmanager_app.auth_serializers import (
    LoginSerializer,
    UserSerializer
)
from testmanager_app.viewsets import BaseViewSet, QueryOptimizerMixin, CommonFilterMixin

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """用户管理API"""
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """管理员可执行所有操作，普通用户仅可查看和修改自己的信息"""
        if self.action in ['create', 'destroy']:
            return [IsAuthenticated(), IsAdminUser()]
        return super().get_permissions()

    def get_queryset(self):
        """普通用户只能看到自己的信息"""
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return User.objects.all()
        return User.objects.filter(pk=user.pk)

    def perform_update(self, serializer):
        """普通用户只能修改自己的信息（PUT和PATCH）"""
        instance = self.get_object()
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            if instance.pk != self.request.user.pk:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('无权修改其他用户信息')
        serializer.save()


class FeatureTestCaseViewSet(QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """功能测试用例API"""
    queryset = FeatureTestCase.objects.all()
    serializer_class = FeatureTestCaseSerializer

    select_related_fields = ['project', 'created_by']
    filter_int_fields = ['project']


from rest_framework.exceptions import NotAuthenticated, AuthenticationFailed


class TokenAuthentication(BaseAuthentication):
    """Custom token authentication using AuthToken model."""
    
    def authenticate_header(self, request: Request) -> str:
        """Return WWW-Authenticate header for 401 responses."""
        return 'Token'
    
    def authenticate(self, request: Request) -> tuple[User, AuthToken] | None:
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header or not auth_header.startswith('Token '):
            raise NotAuthenticated('Authorization header is required')
        
        token_key = auth_header.split(' ')[1]
        
        try:
            auth_token = AuthToken.objects.select_related('user').get(
                key=token_key,
                is_active=True
            )
            
            if auth_token.is_expired():
                raise NotAuthenticated('Token has expired')
            
            auth_token.last_used = timezone.now()
            auth_token.save(update_fields=['last_used'])
            
            return (auth_token.user, auth_token)
        except AuthToken.DoesNotExist:
            raise NotAuthenticated('Invalid token')


class LoginView(APIView):
    """User login API - returns token on successful authentication."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'login'
    
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response(
                {'error': 'Invalid username or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        auth_token = AuthToken.create_token(user, expires_in_days=7)
        
        logger.info(f"User logged in: {username}")
        
        return Response({
            'token': auth_token.key,
            'user': {
                'user_id': user.id,
                'username': user.username,
                'token_expires_at': auth_token.expires_at.isoformat() if auth_token.expires_at else None,
            }
        }, status=status.HTTP_200_OK)


class MeView(APIView):
    """Get current authenticated user information."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def get(self, request: Request) -> Response:
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """User logout API - invalidate current token."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def post(self, request: Request) -> Response:
        if hasattr(request, 'auth') and isinstance(request.auth, AuthToken):
            request.auth.delete()
        
        logger.info(f"User logged out: {request.user.username}")
        
        return Response(
            {'message': 'Successfully logged out'},
            status=status.HTTP_200_OK
        )


class RefreshTokenView(APIView):
    """Refresh token API - extend token expiration."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def post(self, request: Request) -> Response:
        if hasattr(request, 'auth') and isinstance(request.auth, AuthToken):
            new_expiration = timezone.now() + timedelta(days=7)
            request.auth.expires_at = new_expiration
            request.auth.save(update_fields=['expires_at'])
            
            logger.info(f"Token refreshed for user: {request.user.username}")
            
            return Response({
                'token': request.auth.key,
                'expires_at': request.auth.expires_at.isoformat(),
                'message': 'Token successfully refreshed'
            }, status=status.HTTP_200_OK)
        
        return Response(
            {'error': 'No valid token found'},
            status=status.HTTP_400_BAD_REQUEST
        )