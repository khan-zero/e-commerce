# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_overview, name='dashboard_overview'),

    # Product Management
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/edit/<slug:slug>/', views.product_edit, name='product_edit'),
    path('products/delete/<slug:slug>/', views.product_delete, name='product_delete'),

    # Order Management
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/update-status/', views.order_update_status, name='order_update_status'),

    # Shop Management (for sellers)
    path('shop-settings/', views.shop_settings, name='shop_settings'),
    path('shop-create/', views.shop_create, name='shop_create'),

    # User Management (for admins)
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),

    # Reviews & Comments (viewing/managing)
    path('reviews/', views.review_list, name='review_list'),
    path('comments/', views.comment_list, name='comment_list'),
]
