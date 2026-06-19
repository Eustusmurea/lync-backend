from django.urls import path, include
from django.contrib.auth.password_validation import validate_password
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers, viewsets
from .models import User
from .permissions import RBACMixin, get_user_permissions, ROLE_PERMISSIONS


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role', 'department', 'phone', 'is_active']
        read_only_fields = ['id']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'password', 'first_name', 'last_name', 'email', 'role', 'department', 'phone']

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            **UserSerializer(request.user).data,
            'permissions': get_user_permissions(request.user),
        })


class PermissionsMatrixView(APIView):
    """Returns the role → permissions map for admin UI."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            role: sorted(perms)
            for role, perms in ROLE_PERMISSIONS.items()
        })


class UserViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('last_name', 'first_name')
    search_fields = ['first_name', 'last_name', 'username', 'email']
    filterset_fields = ['role', 'is_active']

    rbac_map = {
        'list': 'users.view',
        'retrieve': 'users.view',
        'create': 'users.manage',
        'update': 'users.manage',
        'partial_update': 'users.manage',
        'destroy': 'users.manage',
    }

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer


router = DefaultRouter()
router.register('', UserViewSet, basename='user')

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
    path('permissions/', PermissionsMatrixView.as_view(), name='permissions-matrix'),
    path('', include(router.urls)),
]
