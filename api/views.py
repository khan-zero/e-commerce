from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.db.models import Sum, Count, F, ExpressionWrapper, fields # For analytics aggregations
from datetime import timedelta # For analytics date calculations
from decimal import Decimal # For Decimal operations in analytics

# Filtering and search
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

# IMPORTANT: Corrected imports to reference models from the 'core' app
from core.models import (
    Category, Product, ProductImage, CustomUser, Shop,
    Order, OrderItem, Cart, CartItem, OrderStatus,
    Review, Like, Comment
)
# IMPORTANT: Corrected imports to reference serializers from the 'core' app
from core.serializers import (
    CategorySerializer, ProductSerializer, ProductImageSerializer, CustomUserSerializer,
    ShopSerializer, OrderSerializer, OrderItemSerializer, CartSerializer, CartItemSerializer,
    UserRegistrationSerializer,
    ReviewSerializer, LikeSerializer, CommentSerializer
)

# Helper function
from django.utils.text import slugify

# --- Permissions ---
class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit/create, others to read.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True # Allow GET, HEAD, OPTIONS for everyone
        return request.user and request.user.is_staff # Allow write for staff

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it.
    Assumes the object has a 'customer' or 'owner' field.
    """
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True # Admins can do anything
        if request.method in permissions.SAFE_METHODS:
            return True # Allow GET, HEAD, OPTIONS for everyone

        # Check for 'customer' field (e.g., for Order, Cart)
        if hasattr(obj, 'customer') and obj.customer == request.user:
            return True
        # Check for 'user' field (e.g., for Review, Like, Comment)
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        # Check for 'owner' field (e.g., for Shop)
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True
        # For CartItem, OrderItem, check owner of the parent cart/order
        if hasattr(obj, 'cart') and obj.cart.customer == request.user:
            return True
        if hasattr(obj, 'order') and obj.order.customer == request.user:
            return True

        return False

# Custom permission for sellers to manage their own products
class IsSellerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_staff:
            return True
        if request.method in permissions.SAFE_METHODS:
            return True
        # Allow sellers to create products
        if request.method == 'POST' and request.user.is_authenticated and request.user.is_seller:
            # Also ensure they own an active shop
            return hasattr(request.user, 'shop_profile') and request.user.shop_profile.is_active
        return False

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        if request.method in permissions.SAFE_METHODS:
            return True
        # A seller can only modify/delete their own products
        return request.user.is_authenticated and request.user.is_seller and obj.shop.owner == request.user


# --- ViewSets ---

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly] # Only admins can create/update/delete

    # Optional: Auto-generate slug on creation/update if not provided
    def perform_create(self, serializer):
        if not serializer.validated_data.get('slug'):
            serializer.validated_data['slug'] = slugify(serializer.validated_data['name'])
        serializer.save()

    def perform_update(self, serializer):
        if 'name' in serializer.validated_data and not serializer.validated_data.get('slug'):
            serializer.validated_data['slug'] = slugify(serializer.validated_data['name'])
        serializer.save()


class ShopViewSet(viewsets.ModelViewSet):
    queryset = Shop.objects.all().select_related('owner')
    serializer_class = ShopSerializer
    # Only authenticated users can manage shops, read-only for others
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description', 'owner__username']
    ordering_fields = ['name', 'created_at']


    def get_queryset(self):
        # Admins can see all shops. Sellers can only see/manage their own shop.
        if self.request.user.is_staff:
            return Shop.objects.all()
        elif self.request.user.is_authenticated and self.request.user.is_seller:
            # Ensure the user has only one shop (OneToOneField handles this primarily)
            return Shop.objects.filter(owner=self.request.user)
        # For unauthenticated users, show only active shops
        return Shop.objects.filter(is_active=True)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated or not user.is_seller:
            raise PermissionDenied("Only authenticated sellers can create a shop.")

        # Check if the user already owns a shop
        if Shop.objects.filter(owner=user).exists():
            raise ValidationError("You already own a shop. Each seller can only have one shop.")

        serializer.save(owner=user) # Automatically set the owner

    def get_permissions(self):
        # Allow any authenticated user to create a shop (they'll be checked for is_seller in perform_create)
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        # Allow seller to retrieve their own shop or update their own shop
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'my_shop']:
            return [IsOwnerOrAdmin()] # This custom permission checks for owner or admin
        return [self.permission_classes[0]()] # Default permission for list (read-only)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_shop(self, request):
        """
        Retrieves the authenticated user's shop.
        """
        if not request.user.is_seller:
            return Response({'detail': 'You are not registered as a seller.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            shop = Shop.objects.get(owner=request.user)
            serializer = self.get_serializer(shop)
            return Response(serializer.data)
        except Shop.DoesNotExist:
            return Response({'detail': 'Shop not found for this user.'}, status=status.HTTP_404_NOT_FOUND)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().prefetch_related('images', 'category').select_related('shop')
    serializer_class = ProductSerializer
    permission_classes = [IsSellerOrAdmin] # Custom permission
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'shop', 'available'] # Filter by category, shop, availability
    search_fields = ['name', 'description', 'shop__name', 'category__name']
    ordering_fields = ['name', 'price', 'created_at', 'stock']

    def get_queryset(self):
        # Admins see all. Sellers see their own products. Public sees active products from active shops.
        if self.request.user.is_staff:
            return Product.objects.all().prefetch_related('images', 'category').select_related('shop')
        elif self.request.user.is_authenticated and self.request.user.is_seller:
            # A seller can only view/manage products associated with their shop
            try:
                user_shop = self.request.user.shop_profile
                return Product.objects.filter(shop=user_shop).prefetch_related('images', 'category').select_related('shop')
            except Shop.DoesNotExist:
                return Product.objects.none() # Seller with no shop has no products
        return Product.objects.filter(available=True, shop__is_active=True).prefetch_related('images', 'category').select_related('shop')

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_staff:
            # Admin can specify the shop explicitly
            if 'shop' not in self.request.data:
                raise ValidationError("Admin must provide 'shop' ID when creating a product.")
            serializer.save()
        elif user.is_seller:
            try:
                shop = user.shop_profile
                if not shop.is_active:
                    raise PermissionDenied("Your shop must be active to add products.")
                # Automatically set the shop for the seller
                serializer.save(shop=shop)
            except Shop.DoesNotExist:
                raise ValidationError("Seller must have an active shop to add products.")
        else:
            raise PermissionDenied("You do not have permission to create products.")

    def perform_update(self, serializer):
        # Ensure only product's shop owner or admin can update
        if self.request.user.is_staff or serializer.instance.shop.owner == self.request.user:
            serializer.save()
        else:
            raise PermissionDenied("You do not have permission to update this product.")

    def perform_destroy(self, instance):
        # Ensure only product's shop owner or admin can delete
        if self.request.user.is_staff or instance.shop.owner == self.request.user:
            instance.delete()
        else:
            raise PermissionDenied("You do not have permission to delete this product.")


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all().select_related('product')
    serializer_class = ProductImageSerializer
    permission_classes = [IsSellerOrAdmin] # Only sellers or admins can manage images

    def get_queryset(self):
        if self.request.user.is_staff:
            return ProductImage.objects.all()
        elif self.request.user.is_authenticated and self.request.user.is_seller:
            try:
                user_shop = self.request.user.shop_profile
                # Sellers can only manage images of products from their own shop
                return ProductImage.objects.filter(product__shop=user_shop)
            except Shop.DoesNotExist:
                return ProductImage.objects.none()
        return ProductImage.objects.none() # Public users cannot manage images

    def perform_create(self, serializer):
        product_id = self.request.data.get('product')
        if not product_id:
            raise ValidationError({'product': 'Product ID is required.'})

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValidationError({'product': 'Product not found.'})

        if self.request.user.is_staff:
            serializer.save(product=product)
        elif self.request.user.is_authenticated and self.request.user.is_seller:
            try:
                user_shop = self.request.user.shop_profile
                if product.shop != user_shop:
                    raise PermissionDenied("You can only add images to products from your own shop.")
                serializer.save(product=product)
            except Shop.DoesNotExist:
                raise PermissionDenied("Seller must have an active shop to manage product images.")
        else:
            raise PermissionDenied("You do not have permission to add product images.")


class UserRegistrationView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny] # Anyone can register

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all().select_related('shop_profile') # Preload shop profile
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAdminUser] # Default: only admin can list/manage users

    def get_permissions(self):
        # Allow authenticated users to retrieve/update their own profile
        if self.action in ['retrieve', 'update', 'partial_update', 'me']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()] # Only admin for list, create, destroy

    def get_queryset(self):
        if self.request.user.is_staff:
            return CustomUser.objects.all().select_related('shop_profile')
        # Allow users to only see their own profile
        return CustomUser.objects.filter(id=self.request.user.id).select_related('shop_profile')

    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Endpoint for authenticated users to view and update their own profile.
        """
        user = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        elif request.method in ['PUT', 'PATCH']:
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().prefetch_related('items__product').select_related('customer')
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated] # Only authenticated users can see/create orders
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_paid', 'status']
    ordering_fields = ['created_at', 'total_amount']

    def get_queryset(self):
        # Admins can see all orders. Regular users can only see their own orders.
        if self.request.user.is_staff:
            return Order.objects.all().prefetch_related('items__product').select_related('customer')
        return Order.objects.filter(customer=self.request.user).prefetch_related('items__product').select_related('customer')

    def perform_create(self, serializer):
        # Ensure the order is created for the authenticated user
        customer = self.request.user
        if not customer.is_authenticated:
            raise PermissionDenied("Authentication required to create an order.")

        # In a real scenario, this would likely come from a Cart checkout process
        # For simplicity, we'll assume an order is created with no items initially,
        # or items are passed in the request data (which the current serializer doesn't directly support for creation)
        # A more robust system would have an @action 'checkout' on the CartViewSet.

        # Let's assume for now the user is creating an empty order or populating it via a separate endpoint/admin
        # If you want to create an order with items from the request, you'd need to override create more extensively
        # to handle `items` within the validated_data.
        serializer.save(customer=customer, status=OrderStatus.PENDING, total_amount=0) # Set default status and total

    def perform_update(self, serializer):
        # Prevent regular users from changing is_paid or status directly
        if not self.request.user.is_staff:
            if 'is_paid' in serializer.validated_data:
                del serializer.validated_data['is_paid']
            if 'status' in serializer.validated_data and serializer.instance.status != serializer.validated_data['status']:
                # Only allow specific status transitions if you implement them
                raise PermissionDenied("You cannot change the order status directly.")
        super().perform_update(serializer)

    def get_permissions(self):
        # Admins can do anything. Owners can view, but not create/update/delete status/paid.
        if self.action in ['retrieve', 'my_orders']: # Added 'my_orders'
            return [IsOwnerOrAdmin()] # Allow owner to retrieve
        elif self.action == 'create':
            return [permissions.IsAuthenticated()] # Only authenticated users can create
        # By default, only admin can list, update, delete
        return [permissions.IsAdminUser()]

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_orders(self, request):
        """
        Retrieves all orders for the authenticated user.
        Corresponds to JS: GET /api/orders/my
        """
        queryset = self.get_queryset() # This already filters by request.user for non-staff
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def add_item(self, request, pk=None):
        """Admin only: Adds an item to an existing order."""
        order = self.get_object()
        serializer = OrderItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']

        # Check product availability
        if product.stock < quantity:
            return Response({'detail': f"Not enough stock for {product.name}. Available: {product.stock}"},
                            status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            OrderItem.objects.create(
                order=order,
                product=product,
                price=product.price, # Capture current price
                quantity=quantity
            )
            product.stock -= quantity # Reduce stock
            product.save()

            # Recalculate total amount for the order
            order.total_amount = order.get_total_cost()
            order.save()

        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser, IsSellerOrAdmin]) # Added IsSellerOrAdmin
    def update_status(self, request, pk=None):
        """Admin/Seller only: Updates the status of an order."""
        order = self.get_object()
        new_status = request.data.get('status')
        if not new_status or new_status not in [choice[0] for choice in OrderStatus.choices]:
            return Response({'detail': 'Invalid status provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Additional check for sellers: can only update status of orders for their own products
        if self.request.user.is_seller and not self.request.user.is_staff:
            # Check if all products in the order belong to this seller's shop
            order_products_shops = set(item.product.shop for item in order.items.all())
            if not order_products_shops: # Empty order
                raise ValidationError("Order contains no products.")

            # If there's more than one shop involved, or the shop is not the seller's, deny.
            if len(order_products_shops) > 1 or list(order_products_shops)[0].owner != self.request.user:
                    raise PermissionDenied("You can only update orders that exclusively contain products from your shop.")
            # If the seller is trying to change to a status that's not allowed for them (e.g., Refunded)
            # You might want to define specific transitions for sellers vs admins
            # For now, all status changes are allowed if they own the products in the order.


        order.status = new_status
        order.save()
        serializer = self.get_serializer(order)
        return Response(serializer.data)


class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all().prefetch_related('items__product').select_related('customer')
    serializer_class = CartSerializer
    # Default permission for list/retrieve/etc.
    permission_classes = [permissions.IsAuthenticated] # Still requires auth for general cart management

    def get_queryset(self):
        # Admins can see all carts. Regular users can only see their own cart.
        if self.request.user.is_staff:
            return Cart.objects.all().prefetch_related('items__product').select_related('customer')
        return Cart.objects.filter(customer=self.request.user).prefetch_related('items__product').select_related('customer')

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated:
            # This perform_create is for explicitly creating a cart, which is usually done
            # for authenticated users. Anonymous cart creation is handled by get_or_create in actions.
            raise PermissionDenied("Authentication required to explicitly create a cart.")

        if Cart.objects.filter(customer=user).exists():
            raise ValidationError("You already have an active cart.")

        serializer.save(customer=user)

    def get_object(self):
        # This method is used for detail actions (retrieve, update, destroy).
        # We'll override it to allow authenticated users to access their own cart
        # without needing the PK in the URL for certain actions, or to ensure
        # they only access their own cart if a PK is provided.
        if self.request.user.is_staff:
            # Admin can access any cart by PK
            return super().get_object()

        # For regular authenticated users, ensure they only access their own cart
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            try:
                # If a PK is provided, ensure it's the user's cart
                obj = Cart.objects.get(pk=self.kwargs['pk'], customer=self.request.user)
                self.check_object_permissions(self.request, obj)
                return obj
            except Cart.DoesNotExist:
                raise status.HTTP_404_NOT_FOUND

        # For actions like 'my_cart' or 'checkout' which don't necessarily use a PK in URL
        # the action method itself will handle getting the object.
        return super().get_object()


    def get_permissions(self):
        # Permissions for different actions
        if self.action == 'create': # Explicit cart creation (usually for authenticated users)
            return [permissions.IsAuthenticated()]
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            # For specific cart operations by ID, ensure owner or admin
            return [IsOwnerOrAdmin()]
        if self.action in ['my_cart', 'add_item', 'remove_item', 'checkout']:
            # These actions need custom logic for anonymous users
            return [permissions.AllowAny()] # Allow any user to hit these endpoints
        return [permissions.IsAdminUser()] # Default for list (admin only) or other unhandled actions


    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def my_cart(self, request):
        """
        Retrieves the authenticated user's cart or creates/retrieves an anonymous cart.
        """
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(customer=request.user, defaults={'session_key': None})
            # If an anonymous cart exists for this session, merge it
            if request.session.session_key:
                anonymous_cart = Cart.objects.filter(session_key=request.session.session_key, customer__isnull=True).first()
                if anonymous_cart and anonymous_cart != cart:
                    # Merge anonymous cart items into authenticated cart
                    with transaction.atomic(): # Ensure atomicity for merge
                        for item in anonymous_cart.items.all():
                            existing_item, created_item = CartItem.objects.get_or_create(cart=cart, product=item.product, defaults={'quantity': item.quantity, 'price_at_add': item.product.price}) # Capture price_at_add
                            if not created_item:
                                existing_item.quantity += item.quantity
                                existing_item.save()
                            item.delete() # Remove from anonymous cart
                        anonymous_cart.delete() # Delete anonymous cart
                        request.session.pop('cart_id', None) # Clean up session if you stored cart_id there
        else:
            # Anonymous user: use session key
            if not request.session.session_key:
                request.session.save()
            session_key = request.session.session_key
            cart, created_cart = Cart.objects.get_or_create(session_key=session_key, defaults={'customer': None})

        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def add_item(self, request):
        """
        Adds a product to the cart (authenticated or anonymous) or updates its quantity.
        URL: /api/carts/add_item/
        """
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        if not product_id or quantity <= 0:
            return Response({'detail': 'Product ID and a positive quantity are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Determine the cart based on authentication status
        if request.user.is_authenticated:
            cart, created_cart = Cart.objects.get_or_create(customer=request.user, defaults={'session_key': None})
            # If an anonymous cart exists for this session, merge it (logic already in my_cart, but good to ensure here too if this is entry point)
            # This merge logic is better placed in my_cart or a separate utility. For add_item, assume cart is already determined.
            # However, if add_item is the first interaction for an authenticated user with an anonymous cart, it might need to trigger a merge.
            # For now, we'll rely on my_cart or a prior login to handle the merge.
        else:
            # Anonymous user: use session key
            if not request.session.session_key:
                request.session.save()
            session_key = request.session.session_key
            cart, created_cart = Cart.objects.get_or_create(session_key=session_key, defaults={'customer': None})

        # Now, add/update the item in the determined cart
        with transaction.atomic():
            # Check if product is available and has enough stock
            if not product.available:
                return Response({'detail': f"Product '{product.name}' is not available."}, status=status.HTTP_400_BAD_REQUEST)

            cart_item, created_item = CartItem.objects.get_or_create(cart=cart, product=product)

            new_total_quantity = cart_item.quantity + quantity if not created_item else quantity

            if product.stock < new_total_quantity:
                return Response({'detail': f"Not enough stock for {product.name}. Available: {product.stock}, In cart: {cart_item.quantity if not created_item else 0}"},
                                status=status.HTTP_400_BAD_REQUEST)

            cart_item.quantity = new_total_quantity
            if created_item: # Only set price_at_add if it's a new item in cart
                cart_item.price_at_add = product.price
            cart_item.save()

            serializer = self.get_serializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK if not created_item else status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def remove_item(self, request):
        """
        Removes a product from the cart (authenticated or anonymous) or reduces its quantity.
        URL: /api/carts/remove_item/
        """
        product_id = request.data.get('product_id')
        quantity_to_remove = int(request.data.get('quantity', 1))

        if not product_id or quantity_to_remove <= 0:
            return Response({'detail': 'Product ID and a positive quantity are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Determine the cart based on authentication status
        if request.user.is_authenticated:
            cart = get_object_or_404(Cart, customer=request.user)
        else:
            if not request.session.session_key:
                return Response({'detail': 'No active anonymous cart session.'}, status=status.HTTP_404_NOT_FOUND)
            cart = get_object_or_404(Cart, session_key=request.session.session_key, customer__isnull=True)

        try:
            cart_item = CartItem.objects.get(cart=cart, product__id=product_id)
        except CartItem.DoesNotExist:
            return Response({'detail': 'Product not in cart.'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            if cart_item.quantity <= quantity_to_remove:
                cart_item.delete() # Remove item completely
            else:
                cart_item.quantity -= quantity_to_remove # Reduce quantity
                cart_item.save()

            serializer = self.get_serializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def checkout(self, request):
        """
        Processes the authenticated user's cart into an order.
        URL: /api/carts/checkout/
        """
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied("Authentication required to checkout.")

        cart = get_object_or_404(Cart, customer=user) # Get the authenticated user's cart

        if not cart.items.exists():
            return Response({'detail': 'Your cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        # You'll likely need shipping/billing address data in the request here
        # For simplicity, let's pull from user's default address or require it in request.data
        shipping_address_line1 = request.data.get('shipping_address_line1', getattr(user, 'address', '')) # Using getattr for safety
        shipping_city = request.data.get('shipping_city', '')
        shipping_zip_code = request.data.get('shipping_zip_code', '')
        shipping_country = request.data.get('shipping_country', 'Uzbekistan') # Default country for Tashkent context

        if not all([shipping_address_line1, shipping_city, shipping_zip_code, shipping_country]):
             return Response({'detail': 'Full shipping address is required for checkout.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Create the Order
            order = Order.objects.create(
                customer=user,
                shipping_address_line1=shipping_address_line1,
                shipping_address_line2=request.data.get('shipping_address_line2', ''),
                shipping_city=shipping_city,
                shipping_state=request.data.get('shipping_state', ''),
                shipping_zip_code=shipping_zip_code,
                shipping_country=shipping_country,
                billing_address_line1=request.data.get('billing_address_line1', shipping_address_line1),
                billing_address_line2=request.data.get('billing_address_line2', request.data.get('shipping_address_line2', '')),
                billing_city=request.data.get('billing_city', shipping_city),
                billing_state=request.data.get('billing_state', request.data.get('shipping_state', '')),
                billing_zip_code=request.data.get('billing_zip_code', shipping_zip_code),
                billing_country=request.data.get('billing_country', shipping_country),
                status=OrderStatus.PENDING, # Initial status
            )

            total_order_cost = Decimal('0.00') # Initialize with Decimal
            # Move CartItems to OrderItems and update product stock
            for cart_item in cart.items.all():
                product = cart_item.product
                quantity = cart_item.quantity

                if product.stock < quantity:
                    # Rollback if stock is insufficient for any item
                    raise ValidationError(f"Product '{product.name}' is out of stock for the requested quantity. Available: {product.stock}")
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    price=cart_item.price_at_add, # Use price from cart item (price at the time of adding)
                    quantity=quantity
                )
                product.stock -= quantity # Reduce stock
                product.save()
                total_order_cost += (cart_item.price_at_add * quantity)

            order.total_amount = total_order_cost
            order.save()

            # Clear the cart after successful checkout
            cart.items.all().delete()
            cart.delete() # Or just clear items if cart should persist for the user

            serializer = OrderSerializer(order) # Serialize the newly created order
            return Response(serializer.data, status=status.HTTP_201_CREATED)

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().select_related('product', 'user')
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Authenticated users can create/edit, others read

    def get_queryset(self):
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product__id=product_id)
        return queryset

    def perform_create(self, serializer):
        product_id = self.request.data.get('product')
        if not product_id:
            raise ValidationError({'product': 'Product ID is required to create a review.'})
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValidationError({'product': 'Product not found.'})

        # Ensure a user can only review a product once
        if Review.objects.filter(product=product, user=self.request.user).exists():
            raise ValidationError({'detail': 'You have already reviewed this product.'})

        serializer.save(user=self.request.user, product=product)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrAdmin()] # Only owner or admin can update/delete a review
        return [super().get_permissions()[0]]

    @action(detail=False, methods=['get'], url_path='product/(?P<product_id>[^/.]+)', permission_classes=[permissions.AllowAny])
    def get_reviews_by_product(self, request, product_id=None):
        """
        Retrieves all reviews for a specific product.
        Corresponds to JS: GET /api/comments/product/:productId (though this is for reviews)
        """
        reviews = self.queryset.filter(product__id=product_id)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)


class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all().select_related('product', 'user')
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated] # Only authenticated users can like/unlike

    def perform_create(self, serializer):
        product_id = self.request.data.get('product')
        if not product_id:
            raise ValidationError({'product': 'Product ID is required to like a product.'})
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValidationError({'product': 'Product not found.'})

        # Ensure a user can only like/dislike a product once
        if Like.objects.filter(product=product, user=self.request.user).exists():
            raise ValidationError({'detail': 'You have already liked or disliked this product.'})

        serializer.save(user=self.request.user, product=product)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrAdmin()] # Only owner or admin can update/delete a like
        if self.action in ['add_like', 'remove_like', 'check_like_status']:
            return [permissions.IsAuthenticated()] # Authenticated users for these actions
        if self.action == 'get_likes_count':
            return [permissions.AllowAny()] # Public can see like count
        return [super().get_permissions()[0]] # IsAuthenticated for create/list

    @action(detail=False, methods=['post'], url_path='(?P<product_id>[^/.]+)', permission_classes=[permissions.IsAuthenticated])
    def add_like(self, request, product_id=None):
        """
        Adds a like to a product for the authenticated user.
        Corresponds to JS: POST /api/likes/:productId
        """
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        if Like.objects.filter(user=request.user, product=product).exists():
            return Response({'detail': 'You have already liked this product.'}, status=status.HTTP_409_CONFLICT)

        Like.objects.create(user=request.user, product=product)
        return Response({'detail': 'Product liked successfully.'}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'], url_path='(?P<product_id>[^/.]+)', permission_classes=[permissions.IsAuthenticated])
    def remove_like(self, request, product_id=None):
        """
        Removes a like from a product for the authenticated user.
        Corresponds to JS: DELETE /api/likes/:productId
        """
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            like = Like.objects.get(user=request.user, product=product)
            like.delete()
            return Response({'detail': 'Like removed successfully.'}, status=status.HTTP_200_OK)
        except Like.DoesNotExist:
            return Response({'detail': 'You have not liked this product.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='(?P<product_id>[^/.]+)/status', permission_classes=[permissions.IsAuthenticated])
    def check_like_status(self, request, product_id=None):
        """
        Checks if the authenticated user has liked a specific product.
        Corresponds to JS: GET /api/likes/:productId/status
        """
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        is_liked = Like.objects.filter(user=request.user, product=product).exists()
        return Response({'product_id': product_id, 'is_liked': is_liked}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='(?P<product_id>[^/.]+)/count', permission_classes=[permissions.AllowAny])
    def get_likes_count(self, request, product_id=None):
        """
        Gets the total number of likes for a specific product.
        Corresponds to JS: GET /api/likes/:productId/count
        """
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        count = Like.objects.filter(product=product).count()
        return Response({'product_id': product_id, 'likes_count': count}, status=status.HTTP_200_OK)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all().select_related('product', 'user')
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Authenticated users can create/edit, others read

    def get_queryset(self):
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product__id=product_id)
        return queryset

    def perform_create(self, serializer):
        product_id = self.request.data.get('product')
        comment_text = self.request.data.get('comment_text')

        if not product_id or not comment_text:
            raise ValidationError({'detail': 'Product ID and comment text are required.'})

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValidationError({'product': 'Product not found.'})

        serializer.save(user=self.request.user, product=product, comment_text=comment_text)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrAdmin()] # Only owner or admin can update/delete a comment
        return [super().get_permissions()[0]]

    @action(detail=False, methods=['get'], url_path='product/(?P<product_id>[^/.]+)', permission_classes=[permissions.AllowAny])
    def get_comments_by_product(self, request, product_id=None):
        """
        Retrieves all comments for a specific product.
        Corresponds to JS: GET /api/comments/product/:productId
        """
        comments = self.queryset.filter(product__id=product_id)
        serializer = self.get_serializer(comments, many=True)
        return Response(serializer.data)

class AnalyticsViewSet(viewsets.ViewSet): # Using ViewSet as it's not tied to a single model CRUD
    permission_classes = [permissions.IsAdminUser] # Default to Admin only

    def get_permissions(self):
        # Seller-specific analytics
        if self.action in ['seller_product_sales', 'seller_order_statistics', 'seller_daily_sales_chart']:
            return [permissions.IsAuthenticated(), permissions.IsAdminUser | permissions.IsAuthenticated & permissions.BasePermission.has_permission(self, self.request, self)] # Allows Admin or Authenticated Seller
        return [permissions.IsAdminUser()] # All other analytics are admin-only

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def total_product_sales(self, request):
        """
        Admin only: Gets total sales quantity for top 10 products.
        Corresponds to JS: GET /api/analytics/total-product-sales
        """
        sales_data = OrderItem.objects.values('product__id', 'product__name').annotate(
            total_sold_quantity=Sum('quantity')
        ).order_by('-total_sold_quantity')[:10]
        return Response(list(sales_data))

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def user_statistics(self, request):
        """
        Admin only: Gets user count by role.
        Corresponds to JS: GET /api/analytics/user-statistics
        """
        user_counts = CustomUser.objects.values('role').annotate(count=Count('id'))
        return Response(list(user_counts))

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def order_statistics(self, request):
        """
        Admin only: Gets total orders, total revenue, average order value.
        Corresponds to JS: GET /api/analytics/order-statistics
        """
        total_orders = Order.objects.count()
        total_revenue = Order.objects.aggregate(total_revenue=Sum('total_amount'))['total_revenue'] or Decimal('0.00')
        average_order_value = total_revenue / total_orders if total_orders > 0 else Decimal('0.00')

        return Response({
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'average_order_value': round(average_order_value, 2)
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser | IsSellerOrAdmin])
    def seller_product_sales(self, request):
        """
        Seller/Admin: Gets total sales quantity for seller's top 10 products.
        Corresponds to JS: GET /api/analytics/seller-product-sales
        """
        user = request.user
        if user.is_seller and not user.is_staff:
            try:
                seller_shop = user.shop_profile
            except Shop.DoesNotExist:
                return Response({'detail': 'Seller does not have an associated shop.'}, status=status.HTTP_400_BAD_REQUEST)
            
            sales_data = OrderItem.objects.filter(product__shop=seller_shop).values('product__id', 'product__name').annotate(
                total_sold_quantity=Sum('quantity')
            ).order_by('-total_sold_quantity')[:10]
        elif user.is_staff:
            sales_data = OrderItem.objects.values('product__id', 'product__name', 'product__shop__name').annotate(
                total_sold_quantity=Sum('quantity')
            ).order_by('-total_sold_quantity')[:10]
        else:
            raise PermissionDenied("You do not have permission to access this analytics.")

        return Response(list(sales_data))

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser | IsSellerOrAdmin])
    def seller_order_statistics(self, request):
        """
        Seller/Admin: Gets total orders and revenue for seller's products.
        Corresponds to JS: GET /api/analytics/seller-order-statistics
        """
        user = request.user
        if user.is_seller and not user.is_staff:
            try:
                seller_shop = user.shop_profile
            except Shop.DoesNotExist:
                return Response({'detail': 'Seller does not have an associated shop.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Aggregate based on products belonging to this seller's shop
            orders_queryset = Order.objects.filter(items__product__shop=seller_shop).distinct()
            
            total_orders = orders_queryset.count()
            # Sum of total_amount for orders that contain at least one product from this seller's shop
            # This needs careful calculation if an order contains products from multiple sellers.
            # The JS logic likely summed revenue from order_products specific to the seller.
            # Let's match the JS logic by aggregating on OrderItem.
            total_revenue_for_seller_products = OrderItem.objects.filter(product__shop=seller_shop).aggregate(
                total_revenue=Sum(F('quantity') * F('price'))
            )['total_revenue'] or Decimal('0.00')

            # The JS backend also had 'total_revenue_for_seller' which was total_revenue_for_seller_products
            # and 'total_products_sold_by_seller'
            total_products_sold_by_seller = OrderItem.objects.filter(product__shop=seller_shop).aggregate(
                total_quantity=Sum('quantity')
            )['total_quantity'] or 0

            return Response({
                'total_orders_with_seller_products': total_orders,
                'total_revenue_from_seller_products': total_revenue_for_seller_products,
                'total_products_sold_by_seller': total_products_sold_by_seller
            })
        elif user.is_staff:
            # Admin can see overall stats or filter by seller if needed (not implemented here, but possible)
            return self.order_statistics(request) # Reuse general order statistics for admin
        else:
            raise PermissionDenied("You do not have permission to access this analytics.")


    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser | IsSellerOrAdmin])
    def seller_daily_sales_chart(self, request):
        """
        Seller/Admin: Gets daily sales data for the last 30 days for seller's products.
        Corresponds to JS: GET /api/analytics/seller-daily-sales-chart
        """
        user = request.user
        
        if user.is_seller and not user.is_staff:
            try:
                seller_shop = user.shop_profile
            except Shop.DoesNotExist:
                return Response({'detail': 'Seller does not have an associated shop.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Filter for seller's products
            queryset = OrderItem.objects.filter(
                product__shop=seller_shop,
                order__created_at__gte=timezone.now() - timedelta(days=30)
            )
        elif user.is_staff:
            # Admin can see overall daily sales or for a specific seller if query param is added
            queryset = OrderItem.objects.filter(
                order__created_at__gte=timezone.now() - timedelta(days=30)
            )
            # Optional: Admin can filter by seller_id if needed
            seller_id = request.query_params.get('seller_id')
            if seller_id:
                try:
                    seller_user = CustomUser.objects.get(id=seller_id, is_seller=True)
                    queryset = queryset.filter(product__shop__owner=seller_user)
                except CustomUser.DoesNotExist:
                    return Response({'detail': 'Seller not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            raise PermissionDenied("You do not have permission to access this analytics.")

        sales_data = queryset.annotate(
            sale_date=ExpressionWrapper(
                F('order__created_at__date'),
                output_field=fields.DateField()
            )
        ).values('sale_date').annotate(
            daily_sold_quantity=Sum('quantity'),
            daily_revenue=Sum(F('quantity') * F('price'))
        ).order_by('sale_date')

        return Response(list(sales_data))