from rest_framework import viewsets
from .models import Placement, Banner
from .serializers import PlacementSerializer, BannerSerializer

class PlacementViewSet(viewsets.ModelViewSet):
    queryset = Placement.objects.all()
    serializer_class = PlacementSerializer

class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer