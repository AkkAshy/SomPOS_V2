# auth/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User, Group
from .models import Employee
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['role', 'phone', 'photo']
        extra_kwargs = {
            'photo': {'required': False, 'allow_null': True}
        }

class UserSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer()
    groups = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=Group.objects.all(),
        required=True
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'groups', 'first_name', 'last_name', 'employee']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        employee_data = validated_data.pop('employee')
        groups = validated_data.pop('groups')
        user = User.objects.create_user(**validated_data)
        user.groups.set([Group.objects.get(name=name) for name in groups])
        Employee.objects.create(user=user, **employee_data)
        return user
    
    def update(self, instance, validated_data):
        employee_data = validated_data.pop('employee')
        employee = instance.employee

        # Обновляем поля пользователя
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.save()

        # Обновляем группу
        groups = validated_data.get('groups')
        if groups:
            instance.groups.set([Group.objects.get(name=name) for name in groups])

        # Обновляем данные сотрудника
        employee.role = employee_data.get('role', employee.role)
        employee.phone = employee_data.get('phone', employee.phone)
        employee.photo = employee_data.get('photo', employee.photo)
        employee.save()

        return instance

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    token = serializers.CharField(allow_blank=True, read_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            refresh = RefreshToken.for_user(user)
            return {
                'username': user.username,
                'token': str(refresh.access_token)
            }
        raise serializers.ValidationError("Неверные учетные данные")