from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q  # ✅ Import Q to handle complex queries

from marketing.models import Banner, AdPlacement, Advertisement
from .serializers import BannerSerializer, AdPlacementSerializer, AdvertisementSerializer


# --- Permissions ---

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit/create, others to read.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True  # Allow GET, HEAD, OPTIONS for everyone
        return request.user and request.user.is_staff  # Allow write for staff only


# --- ViewSets ---

class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    permission_classes = [IsAdminOrReadOnly]


class AdPlacementViewSet(viewsets.ModelViewSet):
    queryset = AdPlacement.objects.all()
    serializer_class = AdPlacementSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'  # Allow retrieving by slug


class AdvertisementViewSet(viewsets.ModelViewSet):
    queryset = Advertisement.objects.all().select_related('placement', 'banner', 'product')
    serializer_class = AdvertisementSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter active ads for non-staff users
        if not self.request.user.is_staff:
            today = timezone.now().date()
            queryset = queryset.filter(
                Q(is_active=True) &
                (Q(start_date__isnull=True) | Q(start_date__lte=today)) &
                (Q(end_date__isnull=True) | Q(end_date__gte=today))
            )

        # Optional filter by placement slug for frontend
        placement_slug = self.request.query_params.get('placement_slug')
        if placement_slug:
            queryset = queryset.filter(placement__slug=placement_slug)

        return queryset.order_by('display_order', '-created_at')

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

