from django.db import models


class Transfer(models.Model):
    external_id = models.CharField(max_length=100, unique=True)
    filename = models.CharField(max_length=255)
    local_path = models.CharField(max_length=500)
    fetched_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.filename
