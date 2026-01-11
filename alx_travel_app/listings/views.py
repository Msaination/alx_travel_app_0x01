from rest_framework import viewsets, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from .models import Listing, Booking, Review
from django.contrib.auth.models import User
from .serializers import ListingSerializer, BookingSerializer, ReviewSerializer, UserInfoSerializer, PaymentSerializer
from .services import ChapaServices 
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404





class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserInfoSerializer

class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    permission_classes = [permissions.AllowAny]
    

    def get_permissions(self):
        """ Require authenticaion only whe creating/updating listings
            Anyone can view listing
        """
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(host=self.request.user)
    
    def perform_destroy(self, instance):
        """Only the owner of the listing can delete it"""
        user = self.request.user
        if instance.host != user:
            raise PermissionDenied("You can only delete your own listings.")
        instance.delete()


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    # Displays all bookings for a specific listing
    filterset_fields = ['listing']  # Add the filter for: GET /api/bookings/?listing=<listing_id>

    """Adds the filter by listing in Swagger documentation"""
    # Overrides list method only to attach Swagger metadata
    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'listing',                 # name of the query param
            openapi.IN_QUERY,          # it's in the URL query string
            description="Filter bookings by listing ID",
            type=openapi.TYPE_STRING   # String ID 
        )
    ])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        # When connected to the auth service, make sure to use user.role
        # if hasattr(user, 'role') and user.role == 'host':
        if user.is_staff:
            # Host sees bookings for their listings only
            return Booking.objects.filter(listing__host=user)
        # Guest sees their own bookings
        return Booking.objects.filter(user=user)

    def perform_create(self, request: Request, serializer, *args, **kwargs):
        # Permission makes sure only the guest can create
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking: Booking = serializer.save()

        user = self.request.user
        listing = serializer.validated_data['listing']
        days = (serializer.validated_data['end_date'] - serializer.validated_data['start_date']).days + 1
        serializer.save(
            user=user,
            total_price=listing.price_per_night * days,
            status='pending'
        )
        
        #start Chapa payment process here
        chapa = ChapaServices()
        response = chapa.initialize_payment(
            transaction_id=str(booking.booking_id),
            booking_reference=str(booking.booking_id),
            amount=float(booking.total_price),
            email=request.user.email,
            first_name=request.user.first_name,
            last_name=request.user.last_name
        )
        if response and response.get("status") == "success":
            payment_url = response["data"]["checkout_url"]
            return Response(
                {"payment_url": payment_url},
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {"error": "Failed to initialize payment."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )   
        
    def perform_destroy(self, instance):
        user = self.request.user
        if instance.user != user:
            raise PermissionDenied("You can only delete your own booking.")
        if instance.status == "confirmed":
            raise PermissionDenied("Cannot delete a confirmed booking. Set status to canceled instead.")
        instance.delete()

class VerifyPaymentAPIView(APIView):
    def get(self, request: Request, transaction_id: str, *args, **kwargs):
        booking = get_object_or_404(Booking, booking_id=transaction_id)
        chapa = ChapaServices()
        response = chapa.verify_payment(transaction_id)
        if response and response.get("status") == "success":
            payment_data = response["data"]
            payment_status = payment_data.get("status")

            if payment_status == "successful":
                booking.status = "confirmed"
                booking.save()
                return Response(
                    {
                        "message": "Payment verified and booking confirmed.",
                        "booking_id": str(booking.booking_id),
                        "status": booking.status
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Payment not successful."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {"error": "Failed to verify payment."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
# class VerifyPaymentAPIView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     @swagger_auto_schema(
#         responses={
#             200: openapi.Response(
#                 description="Payment verified successfully",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'message': openapi.Schema(type=openapi.TYPE_STRING),
#                         'booking_id': openapi.Schema(type=openapi.TYPE_STRING),
#                         'status': openapi.Schema(type=openapi.TYPE_STRING),
#                     }
#                 )
#             ),
#             400: "Bad Request",
#             500: "Internal Server Error"
#         }
#     )
#     def get(self, request: Request, transaction_id: str, *args, **kwargs):
#         chapa = ChapaServices()
#         response = chapa.verify_payment(transaction_id)

#         if response and response.get("status") == "success":
#             payment_data = response["data"]
#             booking_id = payment_data.get("tx_ref")
#             payment_status = payment_data.get("status")

#             try:
#                 booking = Booking.objects.get(booking_id=booking_id)
#             except Booking.DoesNotExist:
#                 return Response(
#                     {"error": "Booking not found."},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )

#             if payment_status == "successful":
#                 booking.status = "confirmed"
#                 booking.save()
#                 return Response(
#                     {
#                         "message": "Payment verified and booking confirmed.",
#                         "booking_id": str(booking.booking_id),
#                         "status": booking.status
#                     },
#                     status=status.HTTP_200_OK
#                 )
#             else:
#                 return Response(
#                     {"error": "Payment not successful."},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#         else:
#             return Response(
#                 {"error": "Failed to verify payment."},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer

    def get_permissions(self):
        """ Require authenticaion only whe creating/updating reviews
            Anyone can view reviews
        """
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Reviews is nested in listings: api/listings/<listing_pk>/reviews/"""
        listing_id = self.kwargs.get('listing_pk')
        if listing_id:
            return Review.objects.filter(listing_id=listing_id)
        return Review.objects.all()

    def perform_create(self, serializer):
        listing_id = self.kwargs.get('listing_pk')
        serializer.save(user=self.request.user, listing_id=listing_id)
    
    def perform_destroy(self, instance):
        user = self.request.user
        if instance.user != user:
            raise PermissionDenied("You can only delete your own review.")
        instance.delete()