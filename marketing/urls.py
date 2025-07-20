from rest_framework.routers import DefaultRouter
from .views import PlacementViewSet, BannerViewSet

router = DefaultRouter()
router.register(r'placements', PlacementViewSet)
router.register(r'banners', BannerViewSet)

urlpatterns = router.urls
