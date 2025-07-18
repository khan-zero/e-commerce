# core/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model # Best practice for custom user model
from .models import (
    Category, Product, ProductImage, Shop,
    Order, OrderItem, Cart, CartItem, OrderStatus, # Existing models
    Review, Like, Comment # New models to serialize
)

# Get the CustomUser model
User = get_user_model()

# --- Common Serializers (Inlines first if they're nested) ---

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_main']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug'] # Slug is prepopulated/generated

class ShopSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    # If you want to include owner's phone_number or profile_picture:
    owner_phone_number = serializers.CharField(source='owner.phone_number', read_only=True)
    owner_profile_picture = serializers.ImageField(source='owner.profile_picture', read_only=True)
    
    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'slug', 'description', 'logo',
            'phone_number', 'email', 'is_active', 'owner', 'owner_username',
            'owner_phone_number', 'owner_profile_picture', # Added new fields
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'is_active', 'owner', 'created_at', 'updated_at']

# --- Main Model Serializers ---

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    # Include seller details
    seller_first_name = serializers.CharField(source='shop.owner.first_name', read_only=True)
    seller_last_name = serializers.CharField(source='shop.owner.last_name', read_only=True)
    seller_phone_number = serializers.CharField(source='shop.owner.phone_number', read_only=True)
    seller_profile_picture = serializers.ImageField(source='shop.owner.profile_picture', read_only=True)


    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'stock', 'available',
            'category', 'category_name', 'shop', 'shop_name', 'images',
            'seller_first_name', 'seller_last_name', 'seller_phone_number', 'seller_profile_picture', # Added seller details
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at'] # slug will be auto-generated

    def create(self, validated_data):
        # Handle the automatic assignment of 'shop' when a seller creates a product
        # The view will ensure `request.user.shop_profile` exists.
        if self.context['request'].user.is_seller and not self.context['request'].user.is_staff:
            shop = self.context['request'].user.shop_profile
            validated_data['shop'] = shop
        return super().create(validated_data)


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, source='get_cost')

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_slug', 'price', 'quantity', 'total_cost']
        read_only_fields = ['price'] # Price is set at the time of order creation based on product's current price

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True) # Nested serializer for order items
    customer_username = serializers.CharField(source='customer.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True) # For readable status

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'customer_username', 'created_at', 'updated_at', 'is_paid',
            'shipping_address_line1', 'shipping_address_line2', 'shipping_city',
            'shipping_state', 'shipping_zip_code', 'shipping_country',
            'billing_address_line1', 'billing_address_line2', 'billing_city',
            'billing_state', 'billing_zip_code', 'billing_country',
            'total_amount', 'status', 'status_display', 'items'
        ]
        read_only_fields = [
            'customer', 'created_at', 'updated_at', 'is_paid',
            'total_amount', 'status', 'status_display', 'items'
        ]

class CartItemSerializer(serializers.ModelSerializer):
    # >>>>> MUHIM O'ZGARTIRISH: 'product' fieldini ProductSerializer orqali nest qilish <<<<<
    # Bu 'product' obyektini to'liq ma'lumotlari bilan qaytaradi, ID emas.
    product = ProductSerializer(read_only=True) # Ensure this is the active ProductSerializer
    
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, source='get_cost')

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_cost', 'price_at_add']
        read_only_fields = ['price_at_add']

    def validate(self, data):
        if data['quantity'] <= 0:
            raise serializers.ValidationError("Quantity must be a positive integer.")
        return data


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True) # Nested serializer for cart items
    customer_username = serializers.CharField(source='customer.username', read_only=True)
    total_items = serializers.IntegerField(read_only=True, source='get_total_items')
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, source='get_total_cost')

    class Meta:
        model = Cart
        fields = ['id', 'customer', 'customer_username', 'session_key', 'created_at', 'updated_at', 'items', 'total_items', 'total_cost']
        read_only_fields = ['customer', 'session_key', 'created_at', 'updated_at']

# --- User Serializer ---
class CustomUserSerializer(serializers.ModelSerializer):
    shop_profile = ShopSerializer(read_only=True) # Nest shop profile if available

    class Meta:
        model = User # Use the get_user_model()
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'address', 'profile_picture', 'is_seller', 'role', # Added 'role' field
            'shop_profile' # Include nested shop profile
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'username': {'required': False, 'allow_blank': True} # Allow username to be optional/blank if phone_number is primary
        } 
        read_only_fields = ['is_seller', 'shop_profile', 'role'] # These are set by admin/system, or derived from other logic

    def create(self, validated_data):
        # This serializer is used for CustomUserViewSet, not UserRegistrationView.
        # For creating users via admin or other internal means.
        # Password handling is already in AbstractUser's create_user.
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        # Handle password update separately if provided
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        
        # Prevent direct modification of 'role' through this serializer for non-admin users
        if not self.context['request'].user.is_staff and 'role' in validated_data:
            raise serializers.ValidationError({"role": "You do not have permission to change user roles."})
        
        return super().update(instance, validated_data)

# --- Registration Serializer (For creating new users) ---
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        # Use phone_number as the primary identifier for registration
        fields = ['phone_number', 'email', 'password', 'password2', 'first_name', 'last_name', 'address']
        extra_kwargs = {
            'email': {'required': True}, # Make email required for registration
            'first_name': {'required': True}, # Make first_name required
            'last_name': {'required': True}, # Make last_name required
            'address': {'required': False},
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Check if phone number already exists
        if User.objects.filter(phone_number=data['phone_number']).exists():
            raise serializers.ValidationError({"phone_number": "This phone number is already registered."})
        
        # Check if email already exists (if email is unique)
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})

        return data

    def create(self, validated_data):
        validated_data.pop('password2') # Remove password2 before creating user
        # The create_user method of CustomUserManager will handle setting the password
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            address=validated_data.get('address', ''),
            # Default role is 'buyer' from CustomUser model
        )
        return user

# --- NEW: Review Serializer ---
class ReviewSerializer(serializers.ModelSerializer):
    # Read-only fields for nested user and product info
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)
    user_profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'product', 'product_name', 'user', 'user_first_name', 'user_last_name', 
            'user_profile_picture', 'rating', 'comment_text', 'review_date'
        ]
        read_only_fields = ['user', 'review_date'] # User and date are set by the system

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

# --- NEW: Like Serializer ---
class LikeSerializer(serializers.ModelSerializer):
    # Read-only fields for nested user and product info
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Like
        fields = ['id', 'user', 'user_first_name', 'user_last_name', 'product', 'product_name', 'created_at']
        read_only_fields = ['user', 'created_at'] # User and date are set by the system

    def create(self, validated_data):
        # Custom validation to prevent duplicate likes (handled by unique_together in model too)
        user = self.context['request'].user
        product = validated_data['product']
        if Like.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError("You have already liked this product.")
        return super().create(validated_data)

# --- NEW: Comment Serializer ---
class CommentSerializer(serializers.ModelSerializer):
    # Read-only fields for nested user and product info
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)
    user_profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Comment
        fields = [
            'id', 'product', 'product_name', 'user', 'user_first_name', 'user_last_name', 
            'user_profile_picture', 'comment_text', 'created_at'
        ]
        read_only_fields = ['user', 'created_at'] # User and date are set by the system

    def validate_comment_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Comment text cannot be empty.")
        return value

