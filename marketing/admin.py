# marketing/admin.py

from django.contrib import admin
from .models import Banner, AdPlacement, Advertisement

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'display_order', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    ordering = ('display_order',)

@admin.register(AdPlacement)
class AdPlacementAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)} # Auto-fill slug from name

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('placement', 'get_content_type', 'is_active', 'display_order', 'start_date', 'end_date')
    list_filter = ('placement', 'is_active', 'start_date', 'end_date')
    search_fields = ('placement__name', 'title', 'description', 'banner__title', 'product__name')
    raw_id_fields = ('banner', 'product', 'placement') # Use raw_id_fields for FKs to improve admin performance with many objects
    fieldsets = (
        (None, {
            'fields': ('placement', 'title', 'description', 'is_active', 'display_order')
        }),
        ('Content', {
            'fields': ('banner', 'product'),
            'description': 'Choose either a Banner OR a Product to display as an advertisement.'
        }),
        ('Scheduling', {
            'fields': ('start_date', 'end_date'),
            'classes': ('collapse',)
        }),
    )

    def get_content_type(self, obj):
        if obj.banner:
            return f"Banner: {obj.banner.title}"
        elif obj.product:
            return f"Product: {obj.product.name}"
        return "N/A"
    get_content_type.short_description = "Content"
