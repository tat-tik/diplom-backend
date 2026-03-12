from django.shortcuts import render
import json

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.viewsets import ViewSet, ModelViewSet
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User


from filestorage.models import Storages
from filestorage.functions import mk_storage, replace_delete_user_storage
from users.permissions import IsAdmin, IsAdminOrOwner, IsNotOwnerDeleteOrReadPatchOnly, IsNotFirstAdminOrReadOnly
from users.serializers import LoginRequestSerializer, UserRegSerializer, UsersGetSerializer, UserGetSerializer, \
    UserUpdateByAdminSerializer, UserUpdateByUserSerializer


# Create your views here.

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def users_get(request):
    users = User.objects.all().prefetch_related('storage').order_by('id')
    serializer = UsersGetSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated, IsAdminOrOwner, IsNotOwnerDeleteOrReadPatchOnly, IsNotFirstAdminOrReadOnly])
def user_api(request, id):
    if request.method == 'GET':
        try:
            user = User.objects.get(id=id)
            ser = UserGetSerializer(user)
            return Response(ser.data)
        except User.DoesNotExist:
            return Response({"errors": {"user": ["User not found"]}}, status=404)

    if request.method == 'PATCH':
        try:
            user = User.objects.get(id=id)
            if request.user.is_superuser is True:
                serializer = UserUpdateByAdminSerializer(instance=user, data=request.data, partial=True)
            else:
                serializer = UserUpdateByUserSerializer(instance=user, data=request.data, partial=True)
            if serializer.is_valid():
                password = serializer.validated_data.pop('password', None)
                if password is not None:
                    user.set_password(password)
                    update_session_auth_hash(request, user)
                serializer.save()
                return Response({f'status update user': True}, status=200)
            return Response({"errors": serializer.errors}, status=400)
        except User.DoesNotExist:
            return Response({"errors": {"user": ["User not found"]}}, status=404)

    if request.method == 'DELETE':
        try:
            user = User.objects.get(id=id)
            replace_delete_user_storage(user.storage.id)
            user.delete()
            return Response({f'status delete user': True}, status=200)
        except User.DoesNotExist:
            return Response({"errors": {"user": ["User not found"]}}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def user_reg(request):
    serializer = UserRegSerializer(data=request.data)
    if serializer.is_valid():
        user_new = User.objects.create_user(username=request.data['username'], first_name=request.data['first_name'],
                                            email=request.data['email'], password=request.data['password'])
        storage_user_new = Storages.objects.create(user_id=user_new.id, count_files=0, total_files_size=0)
        mk_storage(storage_user_new.id)
        authenticated_user = authenticate(**serializer.validated_data)
        if authenticated_user is not None:
            login(request, authenticated_user)
            return Response({'status reg': True, 'status login': True, 'user': user_new.id,
                             'storage': authenticated_user.storage.id, 'admin': authenticated_user.is_superuser},
                            status=201)
        else:
            return Response({"errors": {"username": ["Invalid credentials"]}}, status=403)
    else:
        return Response({"errors": serializer.errors}, status=400)


class UsersLogin(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    @staticmethod
    def get(request, *args, **kwargs):  # Убрали format, используем *args, **kwargs
        logout(request)
        return Response({'logout status': 'Success'}, status=200)

    @staticmethod
    def post(request):
        serializer = LoginRequestSerializer(data=request.data)
        if serializer.is_valid():
            authenticated_user = authenticate(**serializer.validated_data)
            if authenticated_user is not None:
                login(request, authenticated_user)
                return Response(
                    {
                        'status login': True,
                        'user': authenticated_user.id,
                        'storage': authenticated_user.storage.id,
                        'admin': authenticated_user.is_superuser
                    },
                    status=201
                )
            else:
                return Response({"errors": {"username": ["Invalid credentials"]}}, status=403)
        return Response({"errors": serializer.errors}, status=400)