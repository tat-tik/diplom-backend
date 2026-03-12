import re
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import Storages, StorageFiles


class UserGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class StoragesGetSerializer(serializers.ModelSerializer):
    user = UserGetSerializer(read_only=True)

    class Meta:
        model = Storages
        fields = ['id', 'last_update', 'user']


class StorageByUserIdGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Storages
        fields = ['user_id']


class FileGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageFiles
        fields = ['id', 'file_name', 'file_size', 'comment', 'date_load', 'date_download', 'public_url']


class FileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageFiles
        fields = ['file_name', 'comment']

    def validate(self, attrs):
        file_name_regexp = re.compile(r'^[0-9a-zA-Zа-яА-Я_\-. ]+$')
        if 'file_name' in attrs:
            if len(attrs['file_name']) > 255:
                raise ValidationError({'file_name': 'file_name validation error: max length 255'})
            if file_name_regexp.match(attrs['file_name']) is None:
                raise ValidationError({'file_name': 'file_name validation error: invalid characters'})
        if 'comment' in attrs and attrs['comment'] is not None:
            if len(attrs['comment']) > 255:
                raise ValidationError({'comment': 'comment validation error: max length 255'})

        return attrs
