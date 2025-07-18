# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
# Import your core app ViewSets
from core.views import (
    CategoryViewSet, ProductViewSet, ProductImageViewSet,
    UserRegistrationView, CustomUserViewSet, ShopViewSet,
    OrderViewSet, CartViewSet,
    ReviewViewSet, LikeViewSet, CommentViewSet, AnalyticsViewSet # NEW: Import new ViewSets
)
# Import your new marketing app ViewSets (already here)
from .views import BannerViewSet, AdPlacementViewSet, AdvertisementViewSet


router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'product-images', ProductImageViewSet)
router.register(r'users', CustomUserViewSet)
router.register(r'shops', ShopViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'carts', CartViewSet) # Keep this for general cart list/retrieve (admin)

# >>>>> NEW: Register Marketing App ViewSets (already here) <<<<<
router.register(r'marketing/banners', BannerViewSet)
router.register(r'marketing/placements', AdPlacementViewSet)
router.register(r'marketing/advertisements', AdvertisementViewSet)

# >>>>> NEW: Register Review, Like, Comment ViewSets <<<<<
router.register(r'reviews', ReviewViewSet)
router.register(r'likes', LikeViewSet, basename='like') # basename is important for custom actions
router.register(r'comments', CommentViewSet)
# AnalyticsViewSet is a ViewSet, not ModelViewSet, so it needs custom URL patterns
# We will define its actions explicitly below.


urlpatterns = [
    # --- Savatga oid maxsus URL'lar (UMUMIY router.urls'dan OLDIN kelishi SHART!) ---
    path('carts/my-cart/', CartViewSet.as_view({'get': 'my_cart'}), name='my-cart'),
    path('carts/add-item/', CartViewSet.as_view({'post': 'add_item'}), name='cart-add-item'),
    path('carts/remove-item/', CartViewSet.as_view({'post': 'remove_item'}), name='cart-remove-item'),
    path('carts/checkout/', CartViewSet.as_view({'post': 'checkout'}), name='cart-checkout'),

    # --- Router tomonidan yaratilgan URL'larni kiritish (maxsus URL'lardan KEYIN) ---
    path('', include(router.urls)),

    # --- Boshqa umumiy API URL'lar ---
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('me/', CustomUserViewSet.as_view({'get': 'me', 'put': 'me', 'patch': 'me'}), name='user-me'),
    
    # --- NEW: Review URLs ---
    # GET /api/reviews/product/:productId (custom action)
    path('reviews/product/<int:product_id>/', ReviewViewSet.as_view({'get': 'get_reviews_by_product'}), name='product-reviews'),

    # --- NEW: Like URLs ---
    # POST /api/likes/:productId (custom action)
    path('likes/<int:product_id>/', LikeViewSet.as_view({'post': 'add_like', 'delete': 'remove_like'}), name='product-like-toggle'),
    # GET /api/likes/:productId/status (custom action)
    path('likes/<int:product_id>/status/', LikeViewSet.as_view({'get': 'check_like_status'}), name='product-like-status'),
    # GET /api/likes/:productId/count (custom action)
    path('likes/<int:product_id>/count/', LikeViewSet.as_view({'get': 'get_likes_count'}), name='product-like-count'),

    # --- NEW: Comment URLs ---
    # GET /api/comments/product/:productId (custom action)
    path('comments/product/<int:product_id>/', CommentViewSet.as_view({'get': 'get_comments_by_product'}), name='product-comments'),

    # --- NEW: Analytics URLs (from AnalyticsViewSet) ---
    path('analytics/total-product-sales/', AnalyticsViewSet.as_view({'get': 'total_product_sales'}), name='analytics-total-product-sales'),
    path('analytics/user-statistics/', AnalyticsViewSet.as_view({'get': 'user_statistics'}), name='analytics-user-statistics'),
    path('analytics/order-statistics/', AnalyticsViewSet.as_view({'get': 'order_statistics'}), name='analytics-order-statistics'),
    path('analytics/seller-product-sales/', AnalyticsViewSet.as_view({'get': 'seller_product_sales'}), name='analytics-seller-product-sales'),
    path('analytics/seller-order-statistics/', AnalyticsViewSet.as_view({'get': 'seller_order_statistics'}), name='analytics-seller-order-statistics'),
    path('analytics/seller-daily-sales-chart/', AnalyticsViewSet.as_view({'get': 'seller_daily_sales_chart'}), name='analytics-seller-daily-sales-chart'),
]


