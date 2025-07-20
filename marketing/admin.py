from django.contrib import admin
from .models import Placement, Banner

@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'description')

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'placement', 'is_active', 'created_at')
    list_filter = ('placement', 'is_active')
    search_fields = ('title', 'url')