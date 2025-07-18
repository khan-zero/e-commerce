# api/serializers.py

from rest_framework import serializers
from marketing.models import Banner, AdPlacement, Advertisement # Import your new models
from core.models import Product # Import Product if you want to nest it in AdvertisementSerializer
from core.serializers import ProductSerializer # Import ProductSerializer from core app

# Serializer for Banner model
class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['id', 'title', 'image', 'description', 'link_url', 'display_order', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

# Serializer for AdPlacement model
class AdPlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdPlacement
        fields = ['id', 'name', 'slug', 'description', 'is_active']
        read_only_fields = ['slug'] # Slug is auto-generated

# Serializer for Advertisement model
class AdvertisementSerializer(serializers.ModelSerializer):
    placement_name = serializers.CharField(source='placement.name', read_only=True)
    banner_data = BannerSerializer(source='banner', read_only=True) # Nest Banner data
    product_data = ProductSerializer(source='product', read_only=True) # Nest Product data

    class Meta:
        model = Advertisement
        fields = [
            'id', 'placement', 'placement_name', 'banner', 'banner_data',
            'product', 'product_data', 'title', 'description',
            'start_date', 'end_date', 'display_order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        # 'banner' and 'product' can be written as IDs for POST/PUT/PATCH,
        # but 'banner_data' and 'product_data' are read-only nested representations.
        # 'title' and 'description' here are overrides for the ad itself.

    def validate(self, data):
        # Ensure only one content type is selected (validation from model's clean method)
        banner = data.get('banner')
        product = data.get('product')

        if banner and product:
            raise serializers.ValidationError("An advertisement cannot have both a banner and a product linked.")
        if not banner and not product:
            raise serializers.ValidationError("An advertisement must have either a banner or a product linked.")
        return data
