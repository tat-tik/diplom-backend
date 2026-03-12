from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    message = "Доступ только для администраторов"

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class IsAdminOrOwner(BasePermission):
    message = "Доступ только для администратора или владельца"

    def has_permission(self, request, view):
        if not request.user:
            return False
        return request.user.is_superuser or request.user.id == view.kwargs.get('id')


class IsNotOwnerDeleteOrReadPatchOnly(BasePermission):
    message = "Вы не можете удалить свой собственный аккаунт"

    def has_permission(self, request, view):
        if request.method in ['GET', 'PATCH', 'PUT', 'HEAD', 'OPTIONS']:
            return True
        if request.method == 'DELETE':
            return request.user.id != view.kwargs.get('id')
        return False


class IsNotFirstAdminOrReadOnly(BasePermission):
    FIRST_ADMIN_ID = 1
    message = "Невозможно изменить или удалить первого администратора"

    def has_permission(self, request, view):
        target_id = view.kwargs.get('id')
        if request.method == 'GET':
            return True
        if request.method in ['PATCH', 'PUT']:
            if request.user.id == self.FIRST_ADMIN_ID:
                return True
            return target_id != self.FIRST_ADMIN_ID
        if request.method == 'DELETE':
            return target_id != self.FIRST_ADMIN_ID

        return False
