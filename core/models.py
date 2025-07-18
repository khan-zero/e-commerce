# core/models.py

from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager # Import BaseUserManager
from decimal import Decimal # Import Decimal for safe calculations
from django.utils.translation import gettext_lazy as _ # For translatable strings
from django.utils.text import slugify # For auto-generating slugs
from django.db.models import UniqueConstraint, Q # For unique constraints and complex queries

# Define choices for order status
class OrderStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PROCESSING = 'PROCESSING', 'PROCESSING'
    SHIPPED = 'SHIPPED', 'Shipped'
    DELIVERED = 'DELIVERED', 'Delivered'
    CANCELLED = 'CANCELLED', 'Cancelled'
    REFUNDED = 'REFUNDED', 'Refunded'

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, blank=True) # Make slug blank=True for auto-generation

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name'] 

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

# --- SHOP MODEL ---
class Shop(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shop_profile',
        limit_choices_to={'is_seller': True}
    )
    name = models.CharField(max_length=255, unique=True, help_text="The name of the shop")
    slug = models.SlugField(unique=True, max_length=255, blank=True, help_text="URL-friendly identifier for the shop") # Make blank=True for auto-generation
    description = models.TextField(blank=True, null=True, help_text="A description of the shop")
    logo = models.ImageField(upload_to='shops/logos/', blank=True, null=True, help_text="Shop logo")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=False, help_text="Whether the shop is active and visible")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Shops"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# --- Product Model ---
class ProductImage(models.Model):
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='products/images/')
    alt_text = models.CharField(max_length=255, blank=True, null=True, help_text="Alt text for accessibility")
    is_main = models.BooleanField(default=False, help_text="Set as the main image for the product")

    class Meta:
        verbose_name_plural = "Product Images"

    def __str__(self):
        return f"Image for {self.product.name}"

class Product(models.Model):
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='products',
        help_text="The shop selling this product"
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255, blank=True) # Make blank=True for auto-generation
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    stock = models.IntegerField(default=0)
    available = models.BooleanField(default=True, help_text="Is the product currently available for purchase?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_main_image(self):
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image.image.url
        first_image = self.images.first()
        if first_image:
            return first_image.image.url
        # Ensure STATIC_URL is defined in settings for placeholder.png
        return settings.STATIC_URL + 'placeholder.png'


# Custom User Manager (to handle phone_number as username)
class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError(_('The Phone Number must be set'))
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin') # Set role to admin for superuser

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(phone_number, password, **extra_fields)

class CustomUser(AbstractUser):
    # AbstractUser already defines 'username', 'email', 'first_name', 'last_name'.
    # We will use phone_number as the USERNAME_FIELD.
    # The 'username' field from AbstractUser will still exist but won't be used for login.
    # You might consider making it nullable or removing its unique constraint if it conflicts.
    # For now, we'll keep it as is, but ensure phone_number is unique.
    username = models.CharField(max_length=150, unique=False, blank=True, null=True) # Make username non-unique and nullable

    phone_number = models.CharField(max_length=20, unique=True, help_text="User's phone number, used for login.")
    address = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='users/profile_pictures/', blank=True, null=True)
    is_seller = models.BooleanField(default=False, help_text="Designates whether this user can own a shop.")
    
    # Role field from JS backend
    # We will map 'admin' role to is_staff/is_superuser
    role = models.CharField(
        max_length=10,
        choices=[
            ('buyer', 'Buyer'),
            ('seller', 'Seller'),
            ('admin', 'Admin'),
        ],
        default='buyer',
        help_text="User's role in the system."
    )

    # Django's AbstractUser already has 'first_name', 'last_name', 'email', 'is_active', 'date_joined', 'last_login', 'is_staff', 'is_superuser'
    # We need to explicitly set USERNAME_FIELD and REQUIRED_FIELDS for our custom login.
    USERNAME_FIELD = 'phone_number' # This tells Django to use phone_number for login
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email'] # Fields required when creating a user via createsuperuser command

    objects = CustomUserManager() # Assign our custom manager

    # Existing group and user_permissions related_name are good
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_('The groups this user belongs to. A user will get all permissions granted to each of their groups.'),
        related_name="customuser_groups",
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="customuser_user_permissions",
        related_query_name="customuser_permission",
    )

    class Meta(AbstractUser.Meta): # Inherit meta options from AbstractUser
        swappable = 'AUTH_USER_MODEL' # Important for custom user models
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.phone_number # Use phone_number for string representation

    # Override save method to synchronize 'role' with 'is_staff' and 'is_superuser'
    def save(self, *args, **kwargs):
        if self.role == 'admin':
            self.is_staff = True
            self.is_superuser = True
        else:
            self.is_staff = False
            self.is_superuser = False
        
        # If username is not set, set it to phone_number (or generate unique if needed)
        if not self.username:
            self.username = self.phone_number # Or some other unique identifier if phone_number is used for login only
        
        super().save(*args, **kwargs)

class Order(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_paid = models.BooleanField(default=False)
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True, null=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100, blank=True, null=True)
    shipping_zip_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)

    billing_address_line1 = models.CharField(max_length=255, blank=True, null=True)
    billing_address_line2 = models.CharField(max_length=255, blank=True, null=True)
    billing_city = models.CharField(max_length=100, blank=True, null=True)
    billing_state = models.CharField(max_length=100, blank=True, null=True)
    billing_zip_code = models.CharField(max_length=20, blank=True, null=True)
    billing_country = models.CharField(max_length=100, blank=True, null=True)
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00')) # Ensure default is Decimal
    
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        help_text="Current status of the order"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} by {self.customer.username if self.customer else 'Guest'}"

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    # >>> MUHIM O'ZGARTIRISH: 'price' maydonini null bo'lishiga ruxsat berish <<<
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
    quantity = models.IntegerField(default=1)

    class Meta:
        verbose_name_plural = "Order Items" # Added for better admin display

    def __str__(self):
        return f"{self.quantity} x {self.product.name if self.product else 'Deleted Product'}"

    def get_cost(self):
        # >>> MUHIM O'ZGARTIRISH: self.price None bo'lsa, uni Decimal(0) deb hisoblash <<<
        # Bu TypeError xatosini oldini oladi.
        return (self.price or Decimal('0.00')) * self.quantity

class Cart(models.Model):
    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='cart'
    )
    session_key = models.CharField(max_length=40, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Carts" # Added for better admin display

    def __str__(self):
        if self.customer:
            return f"Cart of {self.customer.username}"
        return f"Anonymous Cart {self.session_key or self.id}"

    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())

    def get_total_cost(self):
        # Ensure Decimal('0.00') is used for sum if no items
        return sum(item.get_cost() for item in self.items.all()) or Decimal('0.00')

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price_at_add = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        unique_together = ('cart', 'product')
        verbose_name_plural = "Cart Items" # Added for better admin display

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Cart {self.cart.id}"

    def get_cost(self):
        # CartItem'da price_at_add mavjud, shuning uchun uni ishlatamiz
        # Agar price_at_add null bo'lsa, 0.00 deb hisoblaymiz
        return (self.price_at_add or Decimal('0.00')) * self.quantity

# --- NEW: Review Model (from JS db.js) ---
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)], # 1 to 5 stars
        help_text="Rating from 1 to 5 stars"
    )
    comment_text = models.TextField(blank=True, null=True)
    review_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-review_date']
        unique_together = ('product', 'user') # One review per user per product
        verbose_name_plural = "Reviews"

    def __str__(self):
        return f"Review for {self.product.name} by {self.user.username} - {self.rating} stars"

# --- NEW: Like Model (from JS db.js) ---
class Like(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user') # A user can only like a product once
        ordering = ['-created_at']
        verbose_name_plural = "Likes"

    def __str__(self):
        return f"Like for {self.product.name} by {self.user.username}"

# --- NEW: Comment Model (from JS db.js) ---
class Comment(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    comment_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Comments"

    def __str__(self):
        return f"Comment on {self.product.name} by {self.user.username}"


