from django.db import models

class Placement(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Banner(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='marketing/banners/')
    url = models.URLField(blank=True, null=True)
    placement = models.ForeignKey(Placement, on_delete=models.SET_NULL, null=True, blank=True, related_name='banners')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title