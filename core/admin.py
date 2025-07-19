from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Category, Product, ProductImage, CustomUser, Shop,
    Order, OrderItem, Cart, CartItem, OrderStatus,
    Review, Like, Comment # NEW: Import new models
)

# --- INLINE CLASSES (Define these first as they are used by other Admins) ---

# Inline for Product Images (to add/edit images directly from the Product admin page)
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1 # Number of empty forms to display

# Inline for Order Items
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0 # No empty forms by default
    readonly_fields = ('price', 'get_cost',) # Show calculated cost, but don't allow editing
    
    def get_cost(self, obj):
        return obj.get_cost()
    get_cost.short_description = 'Item Cost'

# Inline for Cart Items
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('get_cost',) # Show calculated cost, but don't allow editing

    def get_cost(self, obj):
        return obj.get_cost()
    get_cost.short_description = 'Item Cost'


# --- ADMIN CLASSES ---

# Admin for CustomUser
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Ensure 'role' and 'phone_number' are displayed and editable
    fieldsets = UserAdmin.fieldsets + (
        (('Custom Fields', {'fields': ('phone_number', 'address', 'profile_picture', 'is_seller', 'role')}),)
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (('Custom Fields', {'fields': ('phone_number', 'address', 'profile_picture', 'is_seller', 'role')}),)
    )
    # Removed 'email' from list_display
    list_display = ('phone_number', 'first_name', 'last_name', 'role', 'is_staff', 'is_active', 'is_seller')
    list_filter = ('is_staff', 'is_active', 'is_seller', 'role') # Added role to filters
    # Removed 'email' from search_fields
    search_fields = ('phone_number', 'first_name', 'last_name')

# Admin for Shop
@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'owner__phone_number', 'description') # Search by owner's phone_number
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ('owner',) # Good if you have many users
    actions = ['mark_as_active', 'mark_as_inactive']

    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "Selected shops marked as active.")
    mark_as_active.short_description = "Mark selected shops as active"

    def mark_as_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "Selected shops marked as inactive.")
    mark_as_inactive.short_description = "Mark selected shops as inactive"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'shop', 'category', 'price', 'stock', 'available', 'created_at', 'updated_at')
    list_filter = ('available', 'category', 'shop')
    search_fields = ('name', 'description', 'shop__name')
    prepopulated_fields = {'slug': ('name',)}
    date_hierarchy = 'created_at'
    inlines = [ProductImageInline] # This will now work as ProductImageInline is defined above
    raw_id_fields = ('shop',) # Useful if you have many shops

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'total_amount', 'is_paid', 'status', 'created_at')
    list_filter = ('is_paid', 'status', 'created_at')
    search_fields = ('id', 'customer__phone_number', 'shipping_address_line1') # Search by customer's phone_number
    raw_id_fields = ('customer',)
    inlines = [OrderItemInline] # This will now work as OrderItemInline is defined above
    actions = ['mark_as_paid', 'mark_as_shipped', 'mark_as_delivered']

    def mark_as_paid(self, request, queryset):
        queryset.update(is_paid=True, status=OrderStatus.PROCESSING)
        self.message_user(request, "Selected orders marked as paid and processing.")
    mark_as_paid.short_description = "Mark selected orders as paid and processing"

    def mark_as_shipped(self, request, queryset):
        queryset.update(status=OrderStatus.SHIPPED)
        self.message_user(request, "Selected orders marked as shipped.")
    mark_as_shipped.short_description = "Mark selected orders as shipped"

    def mark_as_delivered(self, request, queryset):
        queryset.update(status=OrderStatus.DELIVERED)
        self.message_user(request, "Selected orders marked as delivered.")
    mark_as_delivered.short_description = "Mark selected orders as delivered"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('customer', 'session_key', 'get_total_items', 'get_total_cost', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('customer__phone_number', 'session_key') # Search by customer's phone_number
    raw_id_fields = ('customer',)
    inlines = [CartItemInline] # This will now work as CartItemInline is defined above

    def get_total_items(self, obj):
        return obj.get_total_items()
    get_total_items.short_description = 'Total Items'

    def get_total_cost(self, obj):
        return obj.get_total_cost()
    get_total_cost.short_description = 'Total Cost'


# --- NEW ADMIN CLASSES ---

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'comment_text', 'review_date')
    list_filter = ('rating', 'review_date')
    search_fields = ('product__name', 'user__phone_number', 'comment_text') # Search by user's phone_number
    raw_id_fields = ('product', 'user')
    readonly_fields = ('review_date',)
    ordering = ('-review_date',)

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('product__name', 'user__phone_number') # Search by user's phone_number
    raw_id_fields = ('product', 'user')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'comment_text', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('product__name', 'user__phone_number', 'comment_text') # Search by user's phone_number
    raw_id_fields = ('product', 'user')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


