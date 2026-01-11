from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import ListingViewSet, BookingViewSet, ReviewViewSet, UserViewSet, VerifyPaymentAPIView, ReviewViewSet

router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'users', UserViewSet, basename='users')

# Nested reviews under listings
listings_router = routers.NestedDefaultRouter(router, r'listings', lookup='listing')
listings_router.register(r'reviews', ReviewViewSet, basename='listing-reviews')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(listings_router.urls)),
    
    path('payments/verify/<str:transaction_id>/', VerifyPaymentAPIView.as_view(), name='verify-payment'),  
         
]