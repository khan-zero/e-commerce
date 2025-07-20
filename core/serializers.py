from rest_framework import serializers
from .models import (
    CustomUser, Category, Shop, Product, ProductImage,
    Order, OrderItem, Cart, CartItem, Review, Like, Comment
)

# User related serializers
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('phone_number', 'first_name', 'last_name', 'email', 'password', 'role', 'is_seller')
        extra_kwargs = {'is_seller': {'required': False}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            email=validated_data.get('email', ''),
            role=validated_data.get('role', 'buyer'),
            is_seller=validated_data.get('is_seller', False)
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('phone_number', 'first_name', 'last_name', 'email', 'address', 'profile_picture', 'is_seller', 'role')
        read_only_fields = ('phone_number', 'is_seller', 'role') # Phone number and role should not be changed via profile update

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'phone_number', 'first_name', 'last_name', 'email', 'address', 'profile_picture', 'is_seller', 'role', 'is_staff', 'is_superuser')
        read_only_fields = ('is_staff', 'is_superuser')

# Category Serializer
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

# Product related serializers
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'shop', 'shop_name', 'name', 'slug', 'description', 'price',
            'category', 'category_name', 'stock', 'available', 'images',
            'created_at', 'updated_at'
        )
        read_only_fields = ('slug', 'created_at', 'updated_at')

# Shop Serializer
class ShopSerializer(serializers.ModelSerializer):
    owner_phone_number = serializers.CharField(source='owner.phone_number', read_only=True)

    class Meta:
        model = Shop
        fields = ('id', 'owner', 'owner_phone_number', 'name', 'slug', 'description', 'logo', 'phone_number', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('slug', 'created_at', 'updated_at')

# Order related serializers
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'order', 'product', 'product_name', 'product_price', 'price', 'quantity')
        read_only_fields = ('price',) # Price is captured at the time of order

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_phone_number = serializers.CharField(source='customer.phone_number', read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'customer', 'customer_phone_number', 'created_at', 'updated_at', 'is_paid',
            'shipping_address_line1', 'shipping_address_line2', 'shipping_city', 'shipping_state',
            'shipping_zip_code', 'shipping_country', 'billing_address_line1', 'billing_address_line2',
            'billing_city', 'billing_state', 'billing_zip_code', 'billing_country', 'total_amount', 'status',
            'items'
        )
        read_only_fields = ('created_at', 'updated_at', 'total_amount')

# Cart related serializers
class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ('id', 'cart', 'product', 'product_name', 'product_price', 'quantity', 'price_at_add')
        read_only_fields = ('price_at_add',)

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    customer_phone_number = serializers.CharField(source='customer.phone_number', read_only=True)

    class Meta:
        model = Cart
        fields = ('id', 'customer', 'customer_phone_number', 'session_key', 'created_at', 'updated_at', 'items')
        read_only_fields = ('session_key', 'created_at', 'updated_at')

# Review Serializer
class ReviewSerializer(serializers.ModelSerializer):
    user_phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'product', 'product_name', 'user', 'user_phone_number', 'rating', 'comment_text', 'review_date')
        read_only_fields = ('review_date',)

# Like Serializer
class LikeSerializer(serializers.ModelSerializer):
    user_phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Like
        fields = ('id', 'product', 'product_name', 'user', 'user_phone_number', 'created_at')
        read_only_fields = ('created_at',)

# Comment Serializer
class CommentSerializer(serializers.ModelSerializer):
    user_phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'product', 'product_name', 'user', 'user_phone_number', 'comment_text', 'created_at')
        read_only_fields = ('created_at',)
