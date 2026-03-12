
from django.urls import path
from . import views

app_name = 'filestorage'

urlpatterns = [
    path('storages/', views.storages_get, name='storages-list'),
    path('storages/<int:storage_id>/files/',
         views.storage_files_list,
         name='storage-files-list'),
    path('storages/<int:storage_id>/files/upload/',
         views.storage_files_upload,
         name='storage-files-upload'),
    path('storages/<int:storage_id>/files/<int:file_id>/',
         views.storage_file_detail,
         name='storage-file-detail'),
    path('storages/<int:storage_id>/files/<int:file_id>/update/',
         views.storage_file_update,
         name='storage-file-update'),
    path('storages/<int:storage_id>/files/<int:file_id>/delete/',
         views.storage_file_delete,
         name='storage-file-delete'),
    path('files/<int:file_id>/download/',
         views.download_file_api,
         name='file-download'),
    path('files/<int:file_id>/share/',
         views.download_file_api,
         name='file-share'),
    path('files/public/<str:public_url_token>/',
         views.download_public_file_api,
         name='file-public-download'),
]