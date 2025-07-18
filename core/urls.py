# core/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
    CategoryViewSet, ProductViewSet, ProductImageViewSet,
    UserRegistrationView, CustomUserViewSet, ShopViewSet,
    OrderViewSet, CartViewSet
)

# Router'ni ishga tushiramiz
router = DefaultRouter()

# Konfliktga uchramaydigan ViewSet'larni ro'yxatdan o'tkazamiz
# Ya'ni, 'carts' ViewSet'idan tashqari barchasini bu yerda ro'yxatdan o'tkazamiz.
# Chunki 'carts' uchun ba'zi maxsus URL'larimiz bor, ularni ustuvor qilishimiz kerak.
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'product-images', ProductImageViewSet)
router.register(r'users', CustomUserViewSet)
router.register(r'shops', ShopViewSet)
router.register(r'orders', OrderViewSet)

# 'carts' ViewSet'ini ham ro'yxatdan o'tkazamiz.
# Bu /api/carts/ (list) va /api/carts/{pk}/ (detail) kabi standart URL'larni yaratadi.
# Lekin bizning maxsus 'carts/' URL'larimiz (my-cart, add-item va h.k.)
# urlpatterns ro'yxatida router.urls'dan oldin joylashgani uchun ular birinchi ishlaydi.
router.register(r'carts', CartViewSet)


urlpatterns = [
    # --- Savatga oid maxsus URL'lar (UMUMIY router.urls'dan OLDIN kelishi SHART!) ---
    # Django URL'larni tepadan pastga qarab tekshiradi.
    # Shuning uchun 'carts/my-cart/' kabi aniq manzillar birinchi bo'lishi kerak,
    # aks holda ular 'carts/<int:pk>/' tomonidan noto'g'ri ushlanib qolishi mumkin.
    path('carts/my-cart/', CartViewSet.as_view({'get': 'my_cart'}), name='my-cart'),
    path('carts/add-item/', CartViewSet.as_view({'post': 'add_item'}), name='cart-add-item'),
    path('carts/remove-item/', CartViewSet.as_view({'post': 'remove_item'}), name='cart-remove-item'),
    path('carts/checkout/', CartViewSet.as_view({'post': 'checkout'}), name='cart-checkout'),

    # --- Router tomonidan yaratilgan URL'larni kiritish (maxsus URL'lardan KEYIN) ---
    # Bu /api/categories/, /api/products/ va h.k. manzilarni o'z ichiga oladi.
    # 'carts' uchun esa /api/carts/ (list) va /api/carts/{pk}/ (detail) manzilini kiritadi.
    # Lekin 'carts/my-cart/' va boshqa maxsus manzil allaqachon topilgani uchun,
    # ular carts/{pk}/ tomonidan noto'g'ri ushlanib qolmaydi.
    path('', include(router.urls)),

    # --- Boshqa umumiy API URL'lar ---
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('me/', CustomUserViewSet.as_view({'get': 'me', 'put': 'me', 'patch': 'me'}), name='user-me'),
]
