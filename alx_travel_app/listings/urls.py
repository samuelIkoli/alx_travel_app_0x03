from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ListingViewSet, BookingViewSet, ReviewViewSet, ListingImageViewSet

router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'listing-images', ListingImageViewSet, basename='listingimage')

urlpatterns = [
    path('', include(router.urls)),   # Correct — no extra /api/
]
