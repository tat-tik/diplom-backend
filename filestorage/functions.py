import os
import shutil
import uuid
import json
import binascii
from datetime import datetime
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse
from django.db.models import Sum
from django.conf import settings
from filestorage.models import Storages, StorageFiles
from django.db import transaction
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone


def ensure_media_root():
    media_root = settings.MEDIA_ROOT
    if not media_root:
        media_root = os.path.join(settings.BASE_DIR, 'media')

    if not os.path.exists(media_root):
        os.makedirs(media_root)
    return media_root


storages_dir = ensure_media_root()
recycle_bin_storages_dir = os.path.join(storages_dir, 'recycle_bin_storages')


def mk_system_dirs():
    global storages_dir, recycle_bin_storages_dir
    storages_dir = ensure_media_root()
    recycle_bin_storages_dir = os.path.join(storages_dir, 'recycle_bin_storages')

    if not os.path.exists(storages_dir):
        os.makedirs(storages_dir)

    if not os.path.exists(recycle_bin_storages_dir):
        os.makedirs(recycle_bin_storages_dir)


mk_system_dirs()


def mk_storage(storage_id):
    storage_user_dir = os.path.join(storages_dir, str(storage_id))
    if not os.path.exists(storage_user_dir):
        os.makedirs(storage_user_dir)
    return storage_user_dir


def replace_delete_user_storage(storage_id):
    storage_user_dir = os.path.join(storages_dir, str(storage_id))
    recycle_dir = os.path.join(recycle_bin_storages_dir, str(storage_id))

    if os.path.exists(storage_user_dir):
        shutil.copytree(storage_user_dir, recycle_dir, dirs_exist_ok=True)
        shutil.rmtree(storage_user_dir)
        return True
    return False


def storage_statistic(storage_id):
    storage_user_files = StorageFiles.objects.filter(storage_id=storage_id)
    storage = Storages.objects.get(id=storage_id)
    storage.count_files = storage_user_files.count()
    total_files_size = storage_user_files.aggregate(Sum("file_size"))[
        'file_size__sum']
    storage.total_files_size = total_files_size if total_files_size is not None else 0
    storage.save()


def save_files(request_files, request_comments, storage_id):
    storage_dir = mk_storage(storage_id)
    comments = json.loads(request_comments) if request_comments else {}
    fs = FileSystemStorage(storage_dir)
    files_to_create = []
    for file in request_files:
        uuid_name = str(uuid.uuid4().hex)
        files_to_create.append(StorageFiles(
            storage_id=storage_id,
            file_name=file.name,
            file_name_storage=uuid_name,
            comment=comments.get(f'comment_{file.name}_{file.size}', ''),
            file_size=file.size
        ))
        fs.save(uuid_name, file)

    if files_to_create:
        StorageFiles.objects.bulk_create(files_to_create)
        storage_statistic(storage_id)

    return files_to_create


def delete_file(storage_id, file_id):
    try:
        file = StorageFiles.objects.get(id=file_id, storage_id=storage_id)
        storage_dir = os.path.join(storages_dir, str(storage_id))
        fs = FileSystemStorage(storage_dir)

        file_path = str(file.file_name_storage)

        if fs.exists(file_path):
            fs.delete(file_path)

        with transaction.atomic():
            file.delete()
            storage_statistic(storage_id)

        return True

    except ObjectDoesNotExist:
        return False
    except Exception as e:
        return False


def download_file(file_id):
    try:
        file_object = StorageFiles.objects.get(id=file_id)
        uuid_value = file_object.file_name_storage
        if isinstance(uuid_value, uuid.UUID):
            filename_storage = uuid_value.hex
        else:
            filename_storage = str(uuid_value).replace('-', '')
        path_to_file = os.path.join(storages_dir, str(file_object.storage_id), filename_storage)
        if not os.path.exists(path_to_file):
            return Response({"error": "File not found on disk"}, status=404)

        file_handle = open(path_to_file, 'rb')
        response = FileResponse(
            file_handle,
            as_attachment=True,
            filename=file_object.file_name
        )
        file_object.date_download = timezone.now()
        file_object.save(update_fields=["date_download"])
        return response

    except ObjectDoesNotExist:
        return Response({"error": "File not found"}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)


def create_public_url(file_id):
    try:
        file_object = StorageFiles.objects.get(id=file_id)
        if file_object.public_url is None:
            token = binascii.hexlify(os.urandom(20)).decode()
            file_object.public_url = token
            file_object.save(update_fields=["public_url"])
            return token
        return file_object.public_url

    except ObjectDoesNotExist:
        return None
    except Exception as e:
        return None



def revoke_public_url(file_id):
    try:
        file_object = StorageFiles.objects.get(id=file_id)
        file_object.public_url = None
        file_object.save(update_fields=["public_url"])
        return True
    except ObjectDoesNotExist:
        return False


def download_file_public(public_url):
    try:
        file_object = StorageFiles.objects.get(public_url=public_url)
        filename_storage = str(file_object.file_name_storage)
        path_to_file = os.path.join(storages_dir, str(file_object.storage_id), filename_storage)

        if not os.path.exists(path_to_file):
            return None

        file_handle = open(path_to_file, 'rb')
        response = FileResponse(
            file_handle,
            as_attachment=True,
            filename=file_object.file_name
        )
        file_object.date_download = datetime.now()
        file_object.save(update_fields=["date_download"])
        return response

    except ObjectDoesNotExist:
        return None
    except Exception as e:
        return None