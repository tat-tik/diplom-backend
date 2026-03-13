import re
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth.models import User
from filestorage.models import Storages


class UserRegSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

    @staticmethod
    def validate_password(value):
        password_regexp = re.compile(
            r'^(?=.*[A-Z])'
            r'(?=.*[a-z])'
            r'(?=.*\d)'
            r'(?=.*[!@#$%^&*()\-_+=;:,./?\\|`~\[\]{}])'
            r'.{6,}$'
        )
        if password_regexp.match(value) is None:
            raise ValidationError('Пароль не удовлетворяет требованиям')
        return value

    @staticmethod
    def validate_username(value):
        username_regexp = re.compile(r'^(?=.{4,20}$)[A-Za-z]+[A-Za-z0-9]*$')
        if username_regexp.match(value) is None:
            raise ValidationError('Логин не удовлетворяет требованиям')
        return value

    @staticmethod
    def validate_first_name(value):
        first_name_regexp = re.compile(r'^(?=.{2,20}$)[A-Za-zА-Яа-я]+$')
        if first_name_regexp.match(value) is None:
            raise ValidationError('Имя не удовлетворяет требованиям')
        return value

    @staticmethod
    def validate_email(value):
        email_regexp = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', flags=re.IGNORECASE)
        if email_regexp.match(value) is None:
            raise ValidationError('E-mail не удовлетворяет требованиям')
        return value


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class StorageGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Storages
        exclude = ['user']


class UserGetSerializer(serializers.ModelSerializer):
    storage = StorageGetSerializer(read_only=True)

    class Meta:
        model = User
        exclude = ['password']


class UsersGetSerializer(serializers.ModelSerializer):
    storage = StorageGetSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'date_joined',
            'is_superuser',
            'is_staff',
            'is_active',
            'storage'
        ]


class UserUpdateByAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'is_superuser', 'is_staff', 'is_active']
        read_only_fields = ['id', 'username', 'last_login', 'date_joined', 'groups', 'user_permissions']

    def validate(self, attrs):
        first_last_names_regexp = re.compile(r'^(?=.{2,20}$)[A-Za-zА-Яа-я]+$')
        if self.instance.id == 1 and (
                attrs['is_superuser'] == False or attrs['is_staff'] == False or attrs['is_active'] == False):
            raise ValidationError('first admin attrs validation error')
        if len(attrs['last_name']) > 0 and first_last_names_regexp.match(attrs['last_name']) is None:
            raise ValidationError('last_name validation error')
        if first_last_names_regexp.match(attrs['first_name']) is None:
            raise ValidationError('first_name validation error')
        password = attrs.get('password', None)
        if password is not None and len(password) < 6:
            raise ValidationError('password validation error')

        return attrs


class UserUpdateByUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'password']
        read_only_fields = ['id', 'username', 'email', 'last_login', 'date_joined', 'is_superuser', 'is_staff',
                            'is_active', 'groups', 'user_permissions']

    def validate(self, attrs):
        first_last_names_regexp = re.compile(r'^(?=.{2,20}$)[A-Za-zА-Яа-я]+$')
        password_regexp = re.compile(
            r'^(?=.*[A-Z])'           
            r'(?=.*[a-z])'           
            r'(?=.*\d)'              
            r'(?=.*[!@#$%^&*()\-_+=;:,./?\\|`~\[\]{}])' 
            r'.{6,}$'
        )
        if self.instance.id == 1 and (
                attrs['is_superuser'] == False or attrs['is_staff'] == False or attrs['is_active'] == False):
            raise ValidationError('first admin attrs validation error')
        if len(attrs['last_name']) > 0 and first_last_names_regexp.match(attrs['last_name']) is None:
            raise ValidationError('last_name validation error')
        if first_last_names_regexp.match(attrs['first_name']) is None:
            raise ValidationError('first_name validation error')
        password = attrs.get('password', None)
        if password is not None and password_regexp.match(password) is None:
            raise ValidationError('password validation error')

        return attrs
