from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.db import transaction

from users.permissions import IsAdmin
from filestorage.permissions import IsOwnerOrAdmin, IsOwnerDownloadOrAdmin
from filestorage.serializers import StoragesGetSerializer, FileGetSerializer, FileUpdateSerializer, UserGetSerializer
from filestorage.models import Storages, StorageFiles
from filestorage.functions import save_files, delete_file, download_file, create_public_url, download_file_public

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def storages_get(request):
    storages = Storages.objects.select_related('user').all().order_by('id')
    serializer = StoragesGetSerializer(storages, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def storage_files_list(request, storage_id):
    try:
        files = StorageFiles.objects.filter(storage_id=storage_id).order_by('-date_load')
        storage = Storages.objects.get(id=storage_id)

        files_serializer = FileGetSerializer(files, many=True)
        user_serializer = UserGetSerializer(storage.user)

        return Response({
            'files': files_serializer.data,
            'user': user_serializer.data
        }, status=status.HTTP_200_OK)
    except Storages.DoesNotExist:
        return Response(
            {"error": "Storage not found"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def storage_file_detail(request, storage_id, file_id):
    try:
        file = StorageFiles.objects.get(id=file_id, storage_id=storage_id)
        serializer = FileGetSerializer(file)
        return Response({"file": serializer.data}, status=status.HTTP_200_OK)
    except StorageFiles.DoesNotExist:
        return Response(
            {"error": "File not found"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
@transaction.atomic
def storage_files_upload(request, storage_id):

    request_files = request.FILES.getlist('files[]')

    if not request_files:
        return Response(
            {"error": "No files provided"},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    comments = request.data.get('comments', [])

    try:
        save_files(request_files, comments, storage_id)
        return Response({'status': True}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def storage_file_update(request, storage_id, file_id):
    try:
        file = StorageFiles.objects.get(id=file_id, storage_id=storage_id)
        serializer = FileUpdateSerializer(instance=file, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()

            Storages.objects.filter(id=storage_id).update()
            return Response({'status': True}, status=status.HTTP_200_OK)

        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    except StorageFiles.DoesNotExist:
        return Response(
            {"error": "File not found"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def storage_file_delete(request, storage_id, file_id):

    if delete_file(storage_id, file_id):
        return Response({'status': True}, status=status.HTTP_200_OK)

    return Response(
        {"error": "File not found"},
        status=status.HTTP_404_NOT_FOUND
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsOwnerDownloadOrAdmin])
def download_file_api(request, file_id):

    path_arr = request.path.split('/')[1:-1]


    if len(path_arr) == 3:
        response = download_file(file_id)
        if response:
            return response
        return Response(
            {"error": "File not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    elif len(path_arr) == 4 and path_arr[2] == 'share':
        token = create_public_url(file_id)
        if token:
            return Response({'status': True, 'token': token}, status=status.HTTP_200_OK)
        return Response(
            {"error": "File not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response(
        {"error": "Invalid URL"},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def download_public_file_api(request, public_url_token):
    path_arr = request.path.split('/')[1:-1]
    if len(path_arr) == 5 and path_arr[3] == 'public':
        response = download_file_public(path_arr[-1])
        if response:
            return response

    return Response(
        {"error": "File not found"},
        status=status.HTTP_404_NOT_FOUND
    )