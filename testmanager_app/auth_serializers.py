"""
Authentication serializers with DRF best practices.
"""
from rest_framework import serializers
from django.contrib.auth.models import User


class LoginSerializer(serializers.Serializer):
    """Login request serializer."""
    username = serializers.CharField(
        required=True,
        max_length=150,
        error_messages={
            'required': 'Username is required',
            'blank': 'Username cannot be blank'
        }
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'required': 'Password is required',
            'blank': 'Password cannot be blank'
        }
    )


class UserSerializer(serializers.ModelSerializer):
    """User information serializer."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_staff', 'is_superuser', 'date_joined', 'last_login']
        read_only_fields = fields


class TokenSerializer(serializers.Serializer):
    """Token response serializer."""
    token = serializers.CharField()
    user = UserSerializer()