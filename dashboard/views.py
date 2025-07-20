# dashboard/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, F, ExpressionWrapper, fields, DecimalField
from django.db.models.functions import TruncDate
from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse

from core.models import (
    Category, Product, CustomUser, Shop,
    Order, OrderItem, OrderStatus,
    Review, Comment
)
from core.forms import OrderStatusUpdateForm, ProductForm, ProductImageFormSet
from core.models import Shop # Import Shop model for shop_profile access
from core.forms import ShopForm # Import ShopForm
from core.forms import CustomUserForm # Import CustomUserForm

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

# Helper functions
def is_seller(user):
    return user.is_authenticated and user.is_seller

def is_admin(user):
    return user.is_authenticated and user.is_superuser

def can_manage_products(user):
    return user.is_authenticated and (user.is_seller or user.is_superuser)

# --- Dashboard Overview ---
@login_required
def dashboard_overview(request):
    if request.user.is_superuser:
        total_orders = Order.objects.count()
        total_products = Product.objects.count()
        total_customers = CustomUser.objects.filter(is_seller=False, is_superuser=False).count()
        total_revenue = Order.objects.filter(is_paid=True).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')

        monthly_sales_data = {}
        today = date.today()
        for i in range(6):
            month_start = (today.replace(day=1) - timedelta(days=30*i))
            sales = Order.objects.filter(
                created_at__year=month_start.year,
                created_at__month=month_start.month,
                is_paid=True
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
            monthly_sales_data[month_start.strftime('%Y-%m')] = float(sales)

        category_sales_data = {}
        top_categories = OrderItem.objects.filter(
            order__is_paid=True, product__category__isnull=False
        ).values('product__category__name').annotate(
            total_sales=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()))
        ).order_by('-total_sales')[:5]

        for item in top_categories:
            safe_total_sales = item['total_sales'] if item['total_sales'] is not None else Decimal('0.00')
            category_sales_data[item['product__category__name']] = float(safe_total_sales)

        daily_sales_data = {}
        for i in range(30):
            day = today - timedelta(days=i)
            sales = Order.objects.filter(
                created_at__date=day,
                is_paid=True
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
            daily_sales_data[day.strftime('%Y-%m-%d')] = float(sales)

        context = {
            'total_orders': total_orders,
            'total_products': total_products,
            'total_customers': total_customers,
            'total_revenue': total_revenue,
            'monthly_sales_json': monthly_sales_data,
            'category_sales_json': category_sales_data,
            'daily_sales_json': daily_sales_data,
            'is_admin': True
        }
        return render(request, 'core/dashboard_overview.html', context)

    elif request.user.is_seller:
        try:
            seller_shop = request.user.shop_profile
        except Shop.DoesNotExist:
            return redirect('dashboard:shop_create') # Redirect to create shop if seller has none

        # Seller-specific analytics
        seller_products = Product.objects.filter(shop=seller_shop)
        total_seller_products = seller_products.count()
        total_seller_orders = Order.objects.filter(items__product__shop=seller_shop).distinct().count()
        total_seller_revenue = OrderItem.objects.filter(product__shop=seller_shop).aggregate(
            total_revenue=Sum(F('quantity') * F('price'))
        )['total_revenue'] or Decimal('0.00')

        # Daily sales for seller's products
        seller_daily_sales_data = {}
        today = date.today()
        for i in range(30):
            day = today - timedelta(days=i)
            sales = OrderItem.objects.filter(
                product__shop=seller_shop,
                order__created_at__date=day
            ).aggregate(Sum(F('quantity') * F('price')))['quantity__times__price__sum'] or Decimal('0.00')
            seller_daily_sales_data[day.strftime('%Y-%m-%d')] = float(sales)

        context = {
            'total_seller_products': total_seller_products,
            'total_seller_orders': total_seller_orders,
            'total_seller_revenue': total_seller_revenue,
            'seller_daily_sales_json': seller_daily_sales_data,
            'is_seller': True
        }
        return render(request, 'core/dashboard_overview.html', context)

    else: # Buyer or other roles
        # Redirect buyers to their profile or a general landing page
        return redirect('core:user_profile') # Assuming you have a user profile view in core app

# --- Product Management Views ---
@login_required
def product_list(request):
    if request.user.is_seller and hasattr(request.user, 'shop_profile'):
        products = Product.objects.filter(shop=request.user.shop_profile).order_by('-created_at')
    else:
        products = Product.objects.all().order_by('-created_at')
        if not request.user.is_superuser:
            products = Product.objects.none()

    context = {'products': products}
    return render(request, 'core/product_list.html', context)

@login_required
@user_passes_test(can_manage_products)
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, user=request.user)
        formset = ProductImageFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            product = form.save(commit=False)
            if request.user.is_seller and not request.user.is_superuser:
                try:
                    product.shop = request.user.shop_profile
                except Shop.DoesNotExist:
                    form.add_error(None, "You must have an active shop profile to add products. Please create one first.")
                    return render(request, 'core/product_form.html', {'form': form, 'formset': formset})
            elif request.user.is_superuser:
                # For superusers, the shop should be selected via the form
                # The form's save method will handle it if 'shop' is in fields
                pass # No explicit assignment needed here if form handles it
            product.save()
            formset.instance = product # Associate formset with the saved product
            formset.save()
            return redirect('dashboard:product_list') # Changed to dashboard namespace
    else:
        form = ProductForm(user=request.user)
        formset = ProductImageFormSet()
    context = {'form': form, 'formset': formset}
    return render(request, 'core/product_form.html', context)

@login_required
@user_passes_test(can_manage_products)
def product_edit(request, slug):
    product = get_object_or_404(Product, slug=slug)

    if not request.user.is_superuser and product.shop.owner != request.user:
        raise PermissionDenied("You do not have permission to edit this product.")

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect('dashboard:product_list')
    else:
        form = ProductForm(instance=product)
        formset = ProductImageFormSet(instance=product)
    context = {'form': form, 'formset': formset, 'product': product}
    return render(request, 'core/product_form.html', context)

@login_required
@user_passes_test(can_manage_products)
def product_delete(request, slug):
    product = get_object_or_404(Product, slug=slug)

    if not request.user.is_superuser and product.shop.owner != request.user:
        raise PermissionDenied("You do not have permission to delete this product.")

    if request.method == 'POST':
        product.delete()
        return redirect('dashboard:product_list') # Changed to dashboard namespace
    context = {'product': product}
    return render(request, 'core/product_confirm_delete.html', context)

# --- Order Management Views ---
@login_required
@user_passes_test(lambda u: u.is_seller or u.is_superuser)
def order_list(request):
    if request.user.is_superuser:
        orders = Order.objects.all().order_by('-created_at')
    elif request.user.is_seller and hasattr(request.user, 'shop_profile'):
        orders = Order.objects.filter(items__product__shop=request.user.shop_profile).distinct().order_by('-created_at')
    else:
        orders = Order.objects.none()

    context = {'orders': orders}
    return render(request, 'core/order_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_seller or u.is_superuser)
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.user.is_seller and hasattr(request.user, 'shop_profile'):
        if not order.items.filter(product__shop=request.user.shop_profile).exists():
            return redirect('dashboard:order_list') # Changed to dashboard namespace

    context = {'order': order}
    return render(request, 'core/order_detail.html', context)

@login_required
@user_passes_test(lambda u: u.is_seller or u.is_superuser)
def order_update_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.user.is_seller and hasattr(request.user, 'shop_profile'):
        if not order.items.filter(product__shop=request.user.shop_profile).exists():
            return redirect('dashboard:order_list') # Changed to dashboard namespace

    if request.method == 'POST':
        form = OrderStatusUpdateForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect('dashboard:order_detail', order_id=order.id) # Changed to dashboard namespace
    else:
        form = OrderStatusUpdateForm(instance=order)
    context = {'form': form, 'order': order}
    return render(request, 'core/order_status_update.html', context)

# --- Shop Management Views (for sellers) ---
@login_required
@user_passes_test(is_seller)
def shop_settings(request):
    try:
        shop = request.user.shop_profile
    except Shop.DoesNotExist:
        return redirect('dashboard:shop_create') # Need to implement this view if not part of registration

    if request.method == 'POST':
        form = ShopForm(request.POST, request.FILES, instance=shop)
        if form.is_valid():
            form.save()
            return redirect('dashboard:shop_settings')
    else:
        form = ShopForm(instance=shop)
    context = {'form': form, 'shop': shop}
    return render(request, 'core/shop_settings.html', context)

@login_required
@user_passes_test(is_seller)
def shop_create(request):
    if hasattr(request.user, 'shop_profile') and request.user.shop_profile: # If user already has a shop, redirect to settings
        return redirect('dashboard:shop_settings')

    if request.method == 'POST':
        form = ShopForm(request.POST, request.FILES)
        if form.is_valid():
            shop = form.save(commit=False)
            shop.owner = request.user
            shop.save()
            return redirect('dashboard:shop_settings')
    else:
        form = ShopForm()
    context = {'form': form}
    return render(request, 'core/shop_form.html', context)


# --- User Management Views (for admins) ---
@login_required
@user_passes_test(is_admin)
def user_management(request):
    users = CustomUser.objects.all().order_by('date_joined')
    context = {'users': users}
    return render(request, 'core/user_management.html', context)

@login_required
@user_passes_test(is_admin)
def user_edit(request, user_id):
    user_to_edit = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        form = CustomUserForm(request.POST, request.FILES, instance=user_to_edit)
        if form.is_valid():
            form.save()
            return redirect('dashboard:user_management')
    else:
        form = CustomUserForm(instance=user_to_edit)
    context = {'form': form, 'user_to_edit': user_to_edit}
    return render(request, 'core/user_edit.html', context)

# --- Reviews & Comments Views ---
@login_required
@user_passes_test(lambda u: u.is_seller or u.is_superuser)
def review_list(request):
    if request.user.is_superuser:
        reviews = Review.objects.all().order_by('-review_date')
    elif request.user.is_seller and hasattr(request.user, 'shop_profile'):
        reviews = Review.objects.filter(product__shop=request.user.shop_profile).order_by('-review_date')
    else:
        reviews = Review.objects.none()

    context = {'reviews': reviews}
    return render(request, 'core/review_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_seller or u.is_superuser)
def comment_list(request):
    if request.user.is_superuser:
        comments = Comment.objects.all().order_by('-created_at')
    elif request.user.is_seller and hasattr(request.user, 'shop_profile'):
        comments = Comment.objects.filter(product__shop=request.user.shop_profile).order_by('-created_at')
    else:
        comments = Comment.objects.none()

    context = {'comments': comments}
    return render(request, 'core/comment_list.html', context)

# --- MODIFIED: shop_settings view ---
@login_required
@user_passes_test(is_seller)
def shop_settings(request):
    try:
        shop = request.user.shop_profile # Try to get the shop profile
    except ObjectDoesNotExist:
        # If the user is a seller but has no shop_profile, redirect to create one
        return redirect('core:shop_create') # <-- REDIRECT NEW SELLERS HERE

    if request.method == 'POST':
        form = ShopForm(request.POST, request.FILES, instance=shop)
        if form.is_valid():
            form.save()
            # messages.success(request, 'Shop settings updated successfully.') # Optional: Django messages
            return redirect('core:shop_settings') # Redirect back to settings page
    else:
        form = ShopForm(instance=shop)

    context = {'form': form, 'shop': shop}
    return render(request, 'core/shop_settings.html', context)


# --- NEW: shop_create view ---
@login_required
@user_passes_test(is_seller) # Only sellers should be able to create a shop
def shop_create(request):
    # If the user already has a shop, redirect them to shop settings
    if hasattr(request.user, 'shop_profile') and request.user.shop_profile:
        return redirect('core:shop_settings')

    if request.method == 'POST':
        form = ShopForm(request.POST, request.FILES)
        if form.is_valid():
            shop = form.save(commit=False)
            shop.owner = request.user # Assign the current user as the shop owner
            shop.save()
            # You might want to update CustomUser.is_seller = True here if it's not done elsewhere
            # Or ensure your is_seller logic checks for existence of shop_profile
            # messages.success(request, 'Your shop has been created successfully!') # Optional
            return redirect('core:shop_settings') # Redirect to settings after creation
    else:
        form = ShopForm()
    
    context = {'form': form}
    return render(request, 'core/shop_create.html', context)
