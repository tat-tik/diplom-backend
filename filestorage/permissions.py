from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.core.exceptions import ObjectDoesNotExist
from .models import Storages, StorageFiles


class IsOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if request.method not in SAFE_METHODS:  # SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
            storage_id = view.kwargs.get('storage_id')
            if not storage_id:
                return False
            try:
                Storages.objects.get(id=storage_id, user=request.user)
                return True
            except ObjectDoesNotExist:
                return False
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'storage'):
            return obj.storage.user == request.user
        return False


class IsOwnerDownloadOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if request.method != 'GET':
            return False
        file_id = view.kwargs.get('file_id')
        if not file_id:
            return False
        try:
            StorageFiles.objects.select_related('storage__user').get(
                id=file_id,
                storage__user=request.user
            )
            return True
        except ObjectDoesNotExist:
            return False


class IsOwnerOrReadOnly(BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        if isinstance(obj, Storages):
            return obj.user == request.user
        elif isinstance(obj, StorageFiles):
            return obj.storage.user == request.user
        return False


