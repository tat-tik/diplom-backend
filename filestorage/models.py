from django.db import models
from django.contrib.auth.models import User


class Storages(models.Model):
    user = models.OneToOneField(User, related_name="storage", on_delete=models.CASCADE)
    count_files = models.IntegerField()
    total_files_size = models.BigIntegerField()
    last_update = models.DateTimeField(editable=False, auto_now=True)


class StorageFiles(models.Model):
    storage = models.ForeignKey(Storages, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=255)
    file_name_storage = models.UUIDField(editable=False)
    file_size = models.PositiveBigIntegerField(editable=False)
    comment = models.CharField(max_length=255, null=True, blank=True)
    date_load = models.DateTimeField(editable=False, auto_now_add=True)
    date_download = models.DateTimeField(null=True, blank=True)
    public_url = models.CharField(max_length=255, null=True, blank=True)

