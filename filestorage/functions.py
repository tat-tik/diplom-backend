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


# Проверяем и создаем media директорию при импорте
def ensure_media_root():
    """Проверяет и создает MEDIA_ROOT, если его нет"""
    media_root = settings.MEDIA_ROOT

    # Если MEDIA_ROOT пустой, создаем путь по умолчанию
    if not media_root:
        media_root = os.path.join(settings.BASE_DIR, 'media')
        print(f"Warning: MEDIA_ROOT not set in settings. Using default: {media_root}")

    # Создаем директорию, если её нет
    if not os.path.exists(media_root):
        os.makedirs(media_root)
        print(f"Created media directory: {media_root}")

    return media_root


# Инициализация директорий
storages_dir = ensure_media_root()
recycle_bin_storages_dir = os.path.join(storages_dir, 'recycle_bin_storages')


def mk_system_dirs():
    """Создание системных директорий"""
    global storages_dir, recycle_bin_storages_dir

    # Обновляем пути (на случай, если MEDIA_ROOT изменился)
    storages_dir = ensure_media_root()
    recycle_bin_storages_dir = os.path.join(storages_dir, 'recycle_bin_storages')

    # Создаем основную директорию
    if not os.path.exists(storages_dir):
        os.makedirs(storages_dir)
        print(f"Created main directory: {storages_dir}")

    # Создаем директорию для корзины
    if not os.path.exists(recycle_bin_storages_dir):
        os.makedirs(recycle_bin_storages_dir)
        print(f"Created recycle bin directory: {recycle_bin_storages_dir}")


# Создаем директории при импорте
mk_system_dirs()


def mk_storage(storage_id):
    """Создание директории для конкретного хранилища"""
    storage_user_dir = os.path.join(storages_dir, str(storage_id))
    if not os.path.exists(storage_user_dir):
        os.makedirs(storage_user_dir)
        print(f"Created storage directory: {storage_user_dir}")
    return storage_user_dir  # Возвращаем путь, а не storages_dir


def replace_delete_user_storage(storage_id):
    """Перемещение хранилища пользователя в корзину"""
    storage_user_dir = os.path.join(storages_dir, str(storage_id))
    recycle_dir = os.path.join(recycle_bin_storages_dir, str(storage_id))

    if os.path.exists(storage_user_dir):
        # Копируем в корзину
        shutil.copytree(storage_user_dir, recycle_dir, dirs_exist_ok=True)
        # Удаляем оригинал
        shutil.rmtree(storage_user_dir)
        print(f"Moved storage {storage_id} to recycle bin")
        return True
    return False


def storage_statistic(storage_id):
    """Обновление статистики хранилища"""
    storage_user_files = StorageFiles.objects.filter(storage_id=storage_id)
    storage = Storages.objects.get(id=storage_id)

    storage.count_files = storage_user_files.count()
    total_files_size = storage_user_files.aggregate(Sum("file_size"))[
        'file_size__sum']  # Исправлено: было 'size', стало 'file_size'
    storage.total_files_size = total_files_size if total_files_size is not None else 0
    storage.save()


def save_files(request_files, request_comments, storage_id):
    """Сохранение загруженных файлов"""
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

        # Сохраняем файл
        fs.save(uuid_name, file)
        print(f"Saved file: {file.name} as {uuid_name}")

    # Массовое создание записей в БД
    if files_to_create:
        StorageFiles.objects.bulk_create(files_to_create)
        storage_statistic(storage_id)

    return files_to_create


def delete_file(storage_id, file_id):
    """Удаление файла"""
    try:
        file = StorageFiles.objects.get(id=file_id, storage_id=storage_id)
        storage_dir = os.path.join(storages_dir, str(storage_id))
        fs = FileSystemStorage(storage_dir)

        file_path = str(file.file_name_storage)

        # Удаляем физический файл
        if fs.exists(file_path):
            fs.delete(file_path)
            print(f"Deleted file: {file_path}")
        else:
            print(f"File not found on disk: {file_path}")

        # Удаляем запись из БД в транзакции
        with transaction.atomic():
            file.delete()
            storage_statistic(storage_id)

        return True

    except ObjectDoesNotExist:
        print(f"File with id {file_id} not found in database")
        return False
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False


def download_file(file_id):
    """Скачивание файла"""
    try:
        file_object = StorageFiles.objects.get(id=file_id)

        # ПОЛУЧАЕМ UUID ИЗ БД
        uuid_value = file_object.file_name_storage

        # ПРЕОБРАЗУЕМ В СТРОКУ БЕЗ ДЕФИСОВ
        if isinstance(uuid_value, uuid.UUID):
            # Если это UUID объект
            filename_storage = uuid_value.hex
            print(f"📁 UUID object detected, using hex: {filename_storage}")
        else:
            # Если это строка - убираем дефисы
            filename_storage = str(uuid_value).replace('-', '')
            print(f"📁 String detected, removing hyphens: {filename_storage}")

        # ФОРМИРУЕМ ПУТЬ
        path_to_file = os.path.join(storages_dir, str(file_object.storage_id), filename_storage)

        print(f"📁 Full path: {path_to_file}")
        print(f"📁 File exists: {os.path.exists(path_to_file)}")

        if not os.path.exists(path_to_file):
            print(f"❌ File not found on disk")
            return Response({"error": "File not found on disk"}, status=404)

        file_handle = open(path_to_file, 'rb')
        response = FileResponse(
            file_handle,
            as_attachment=True,
            filename=file_object.file_name
        )
        file_object.date_download = timezone.now()
        file_object.save(update_fields=["date_download"])
        print(f"✅ File downloaded successfully")
        return response

    except ObjectDoesNotExist:
        print(f"❌ File with id {file_id} not found in database")
        return Response({"error": "File not found"}, status=404)
    except Exception as e:
        print(f"❌ Error in download_file: {e}")
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)


def create_public_url(file_id):
    """Создание публичной ссылки на файл"""
    try:
        file_object = StorageFiles.objects.get(id=file_id)
        print(f"🔗 Creating public URL for file {file_id}: {file_object.file_name}")

        if file_object.public_url is None:
            token = binascii.hexlify(os.urandom(20)).decode()
            file_object.public_url = token
            file_object.save(update_fields=["public_url"])
            print(f"✅ Created new token: {token}")
            return token

        print(f"✅ Using existing token: {file_object.public_url}")
        return file_object.public_url

    except ObjectDoesNotExist:
        print(f"❌ File with id {file_id} not found")
        return None
    except Exception as e:
        print(f"❌ Error creating public URL: {e}")
        return None



def revoke_public_url(file_id):
    """Отзыв публичной ссылки"""
    try:
        file_object = StorageFiles.objects.get(id=file_id)
        file_object.public_url = None
        file_object.save(update_fields=["public_url"])
        print(f"Revoked public URL for file {file_id}")
        return True
    except ObjectDoesNotExist:
        print(f"File with id {file_id} not found")
        return False


def download_file_public(public_url):
    """Скачивание файла по публичной ссылке"""
    try:
        print(f"🔗 download_file_public: looking for token={public_url}")

        file_object = StorageFiles.objects.get(public_url=public_url)
        print(f"✅ Found file: {file_object.file_name}")
        print(f"📁 Storage ID: {file_object.storage_id}")
        print(f"📁 File name storage: {file_object.file_name_storage}")

        # Формируем путь к файлу
        filename_storage = str(file_object.file_name_storage)
        path_to_file = os.path.join(storages_dir, str(file_object.storage_id), filename_storage)

        print(f"📁 Path: {path_to_file}")
        print(f"📁 File exists: {os.path.exists(path_to_file)}")

        if not os.path.exists(path_to_file):
            print(f"❌ File not found on disk")
            return None

        file_handle = open(path_to_file, 'rb')
        response = FileResponse(
            file_handle,
            as_attachment=True,
            filename=file_object.file_name
        )

        file_object.date_download = datetime.now()
        file_object.save(update_fields=["date_download"])

        print(f"✅ Public download successful")
        return response

    except ObjectDoesNotExist:
        print(f"❌ No file found with token: {public_url}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None