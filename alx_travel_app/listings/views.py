from django.shortcuts import render
from django.http import HttpResponse

import uuid
from django.http import JsonResponse
from .models import Payment
from .services.chapa import initialize_chapa_transaction

from .services.chapa import verify_chapa_transaction

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Q
from .models import Listing, Booking, Review, ListingImage
from .serializers import (
    ListingSerializer, CreateListingSerializer, BookingSerializer,
    CreateBookingSerializer, ReviewSerializer, HostResponseSerializer,
    BookingStatusSerializer, ListingSearchSerializer, ListingImageSerializer
)

# Create your views here.
def listing_list(request):
    return HttpResponse("List of listings")

def listing_detail(request, pk):
    return HttpResponse(f"Details of listing {pk}")

class ListingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['property_type', 'city', 'country', 'max_guests']
    search_fields = ['title', 'description', 'city', 'country']
    ordering_fields = ['base_price', 'created_at', 'average_rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Listing.objects.filter(status='active')
        
        # Filter by availability if dates provided
        check_in = self.request.query_params.get('check_in')
        check_out = self.request.query_params.get('check_out')
        
        if check_in and check_out:
            # This is a simplified availability check
            unavailable_listings = Booking.objects.filter(
                Q(check_in__lt=check_out) & Q(check_out__gt=check_in),
                status__in=['confirmed', 'active']
            ).values_list('listing_id', flat=True)
            
            queryset = queryset.exclude(id__in=unavailable_listings)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateListingSerializer
        return ListingSerializer
    
    def perform_create(self, serializer):
        serializer.save(host=self.request.user)
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        serializer = ListingSearchSerializer(data=request.data)
        if serializer.is_valid():
            queryset = Listing.objects.filter(status='active')
            
            # Apply filters based on search criteria
            data = serializer.validated_data
            
            if data.get('city'):
                queryset = queryset.filter(city__icontains=data['city'])
            
            if data.get('country'):
                queryset = queryset.filter(country__icontains=data['country'])
            
            if data.get('guests'):
                queryset = queryset.filter(max_guests__gte=data['guests'])
            
            if data.get('property_type'):
                queryset = queryset.filter(property_type=data['property_type'])
            
            if data.get('min_price'):
                queryset = queryset.filter(base_price__gte=data['min_price'])
            
            if data.get('max_price'):
                queryset = queryset.filter(base_price__lte=data['max_price'])
            
            # Availability check
            if data.get('check_in') and data.get('check_out'):
                unavailable_listings = Booking.objects.filter(
                    Q(check_in__lt=data['check_out']) & Q(check_out__gt=data['check_in']),
                    status__in=['confirmed', 'active']
                ).values_list('listing_id', flat=True)
                queryset = queryset.exclude(id__in=unavailable_listings)
            
            # Amenities filter
            if data.get('amenities'):
                amenity_filters = Q()
                for amenity in data['amenities']:
                    amenity_filters |= Q(**{amenity: True})
                queryset = queryset.filter(amenity_filters)
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = ListingSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = ListingSerializer(queryset, many=True)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def bookings(self, request, pk=None):
        listing = self.get_object()
        bookings = listing.bookings.all()
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Booking.objects.all()
        return Booking.objects.filter(guest=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateBookingSerializer
        elif self.action == 'update' and self.request.data.get('status'):
            return BookingStatusSerializer
        return BookingSerializer
    
    def perform_create(self, serializer):
        serializer.save(guest=self.request.user)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.can_be_cancelled:
            booking.status = 'cancelled'
            booking.cancelled_at = timezone.now()
            booking.save()
            serializer = BookingSerializer(booking)
            return Response(serializer.data)
        return Response(
            {'error': 'This booking cannot be cancelled.'},
            status=status.HTTP_400_BAD_REQUEST
        )


class ReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['listing', 'rating', 'is_verified']
    ordering_fields = ['rating', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Review.objects.filter(is_public=True)
    
    def get_serializer_class(self):
        if self.action == 'update' and self.request.data.get('host_response'):
            return HostResponseSerializer
        return ReviewSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def respond(self, request, pk=None):
        review = self.get_object()
        # Check if the current user is the host of the listing
        if review.listing.host != request.user:
            return Response(
                {'error': 'Only the host can respond to this review.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = HostResponseSerializer(review, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListingImageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ListingImageSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return ListingImage.objects.all()
        return ListingImage.objects.filter(listing__host=user)
    
    def perform_create(self, serializer):
        listing = serializer.validated_data['listing']
        # Check if the current user is the host of the listing
        if listing.host != self.request.user:
            raise PermissionError("You can only add images to your own listings.")
        serializer.save()


# ✅ FIXED: this was incorrectly indented inside the class
def start_payment(request):
    amount = request.GET.get("amount")
    email = request.GET.get("email")

    reference = str(uuid.uuid4())  # Unique reference

    chapa_response = initialize_chapa_transaction(amount, email, reference)

    # store payment
    payment = Payment.objects.create(
        booking_reference=reference,
        amount=amount,
        transaction_id=chapa_response["data"]["tx_ref"],
        status="Pending",
    )

    return JsonResponse(chapa_response)


def verify_payment(request, reference):
    chapa_response = verify_chapa_transaction(reference)

    try:
        payment = Payment.objects.get(booking_reference=reference)
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment not found"}, status=404)

    status = chapa_response["data"]["status"]

    if status == "success":
        payment.status = "Completed"
    else:
        payment.status = "Failed"

    payment.save()

    return JsonResponse({"status": payment.status})from django.shortcuts import render
from django.http import HttpResponse
import uuid
from django.http import JsonResponse
from .models import Payment
from .services.chapa import initialize_chapa_transaction
from .services.chapa import verify_chapa_transaction

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Q
from django.utils import timezone  # Added import for timezone
from django.conf import settings  # Added import for settings

# Import Celery tasks
from .tasks import (
    send_booking_confirmation_email, 
    send_booking_cancellation_email,
    send_booking_reminder_email
)

from .models import Listing, Booking, Review, ListingImage
from .serializers import (
    ListingSerializer, CreateListingSerializer, BookingSerializer,
    CreateBookingSerializer, ReviewSerializer, HostResponseSerializer,
    BookingStatusSerializer, ListingSearchSerializer, ListingImageSerializer
)

# Create your views here.
def listing_list(request):
    return HttpResponse("List of listings")

def listing_detail(request, pk):
    return HttpResponse(f"Details of listing {pk}")

class ListingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['property_type', 'city', 'country', 'max_guests']
    search_fields = ['title', 'description', 'city', 'country']
    ordering_fields = ['base_price', 'created_at', 'average_rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Listing.objects.filter(status='active')
        
        # Filter by availability if dates provided
        check_in = self.request.query_params.get('check_in')
        check_out = self.request.query_params.get('check_out')
        
        if check_in and check_out:
            # This is a simplified availability check
            unavailable_listings = Booking.objects.filter(
                Q(check_in__lt=check_out) & Q(check_out__gt=check_in),
                status__in=['confirmed', 'active']
            ).values_list('listing_id', flat=True)
            
            queryset = queryset.exclude(id__in=unavailable_listings)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateListingSerializer
        return ListingSerializer
    
    def perform_create(self, serializer):
        serializer.save(host=self.request.user)
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        serializer = ListingSearchSerializer(data=request.data)
        if serializer.is_valid():
            queryset = Listing.objects.filter(status='active')
            
            # Apply filters based on search criteria
            data = serializer.validated_data
            
            if data.get('city'):
                queryset = queryset.filter(city__icontains=data['city'])
            
            if data.get('country'):
                queryset = queryset.filter(country__icontains=data['country'])
            
            if data.get('guests'):
                queryset = queryset.filter(max_guests__gte=data['guests'])
            
            if data.get('property_type'):
                queryset = queryset.filter(property_type=data['property_type'])
            
            if data.get('min_price'):
                queryset = queryset.filter(base_price__gte=data['min_price'])
            
            if data.get('max_price'):
                queryset = queryset.filter(base_price__lte=data['max_price'])
            
            # Availability check
            if data.get('check_in') and data.get('check_out'):
                unavailable_listings = Booking.objects.filter(
                    Q(check_in__lt=data['check_out']) & Q(check_out__gt=data['check_in']),
                    status__in=['confirmed', 'active']
                ).values_list('listing_id', flat=True)
                queryset = queryset.exclude(id__in=unavailable_listings)
            
            # Amenities filter
            if data.get('amenities'):
                amenity_filters = Q()
                for amenity in data['amenities']:
                    amenity_filters |= Q(**{amenity: True})
                queryset = queryset.filter(amenity_filters)
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = ListingSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = ListingSerializer(queryset, many=True)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def bookings(self, request, pk=None):
        listing = self.get_object()
        bookings = listing.bookings.all()
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Booking.objects.all()
        return Booking.objects.filter(guest=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateBookingSerializer
        elif self.action == 'update' and self.request.data.get('status'):
            return BookingStatusSerializer
        return BookingSerializer
    
    def perform_create(self, serializer):
        booking = serializer.save(guest=self.request.user)
        
        # Generate confirmation number if not present
        if not booking.confirmation_number:
            booking.confirmation_number = str(uuid.uuid4())[:8].upper()
            booking.save()
        
        # Prepare booking data for email
        booking_data = {
            'booking_id': booking.id,
            'confirmation_number': booking.confirmation_number,
            'listing_title': booking.listing.title if hasattr(booking.listing, 'title') else 'Listing',
            'check_in': booking.check_in,
            'check_out': booking.check_out,
            'guests': booking.guests,
            'total_price': booking.total_price,
            'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'status': booking.status,
        }
        
        # Send confirmation email asynchronously using Celery
        send_booking_confirmation_email.delay(
            booking_data=booking_data,
            user_email=self.request.user.email
        )
        
        # If payment is required, initialize payment
        if booking.total_price > 0:
            self.initialize_payment(booking)
    
    def initialize_payment(self, booking):
        """
        Initialize payment for the booking if required.
        """
        try:
            # Generate unique reference for payment
            reference = str(uuid.uuid4())
            
            # Initialize payment with Chapa or your payment provider
            # This is a placeholder - implement based on your payment system
            payment = Payment.objects.create(
                booking=booking,
                amount=booking.total_price,
                reference=reference,
                status='pending',
            )
            
            # You can trigger payment initiation here if needed
            # chapa_response = initialize_chapa_transaction(
            #     str(booking.total_price),
            #     self.request.user.email,
            #     reference
            # )
            
            return payment
            
        except Exception as e:
            print(f"Error initializing payment: {e}")
            return None
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        
        # Check if user has permission to cancel
        if booking.guest != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to cancel this booking.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if booking can be cancelled
        if not hasattr(booking, 'can_be_cancelled') or not booking.can_be_cancelled():
            return Response(
                {'error': 'This booking cannot be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update booking status
        booking.status = 'cancelled'
        booking.cancelled_at = timezone.now()
        booking.save()
        
        # Prepare cancellation data for email
        booking_data = {
            'booking_id': booking.id,
            'confirmation_number': booking.confirmation_number,
            'listing_title': booking.listing.title if hasattr(booking.listing, 'title') else 'Listing',
            'cancellation_date': booking.cancelled_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Send cancellation email asynchronously
        send_booking_cancellation_email.delay(
            booking_data=booking_data,
            user_email=request.user.email
        )
        
        serializer = BookingSerializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        Confirm a pending booking (admin or host only).
        """
        booking = self.get_object()
        
        # Check if user has permission to confirm
        if not request.user.is_staff and booking.listing.host != request.user:
            return Response(
                {'error': 'Only the host or admin can confirm bookings.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        booking.status = 'confirmed'
        booking.confirmed_at = timezone.now()
        booking.save()
        
        # Send confirmation email to guest
        booking_data = {
            'booking_id': booking.id,
            'confirmation_number': booking.confirmation_number,
            'listing_title': booking.listing.title if hasattr(booking.listing, 'title') else 'Listing',
            'check_in': booking.check_in,
            'check_out': booking.check_out,
            'confirmed_at': booking.confirmed_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        send_booking_confirmation_email.delay(
            booking_data=booking_data,
            user_email=booking.guest.email
        )
        
        serializer = BookingSerializer(booking)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Get upcoming bookings for the current user.
        """
        upcoming_bookings = Booking.objects.filter(
            guest=request.user,
            check_in__gte=timezone.now().date(),
            status='confirmed'
        ).order_by('check_in')
        
        serializer = self.get_serializer(upcoming_bookings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def past(self, request):
        """
        Get past bookings for the current user.
        """
        past_bookings = Booking.objects.filter(
            guest=request.user,
            check_out__lt=timezone.now().date()
        ).order_by('-check_out')
        
        serializer = self.get_serializer(past_bookings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def host_bookings(self, request):
        """
        Get bookings for listings owned by the current user (host view).
        """
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get listings owned by the user
        user_listings = Listing.objects.filter(host=request.user)
        bookings = Booking.objects.filter(listing__in=user_listings).order_by('-created_at')
        
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)


class ReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['listing', 'rating', 'is_verified']
    ordering_fields = ['rating', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Review.objects.filter(is_public=True)
    
    def get_serializer_class(self):
        if self.action == 'update' and self.request.data.get('host_response'):
            return HostResponseSerializer
        return ReviewSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def respond(self, request, pk=None):
        review = self.get_object()
        # Check if the current user is the host of the listing
        if review.listing.host != request.user:
            return Response(
                {'error': 'Only the host can respond to this review.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = HostResponseSerializer(review, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListingImageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ListingImageSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return ListingImage.objects.all()
        return ListingImage.objects.filter(listing__host=user)
    
    def perform_create(self, serializer):
        listing = serializer.validated_data['listing']
        # Check if the current user is the host of the listing
        if listing.host != self.request.user:
            raise PermissionError("You can only add images to your own listings.")
        serializer.save()


# Payment views (outside of classes)
@api_view(['GET'])
def start_payment(request):
    """
    Start payment process for a booking.
    """
    amount = request.GET.get("amount")
    email = request.GET.get("email")
    booking_id = request.GET.get("booking_id")
    
    if not amount or not email:
        return JsonResponse(
            {"error": "Amount and email are required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    reference = str(uuid.uuid4())  # Unique reference
    
    # Initialize payment with Chapa
    chapa_response = initialize_chapa_transaction(amount, email, reference)
    
    if chapa_response.get("status") != "success":
        return JsonResponse(
            {"error": "Failed to initialize payment."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Store payment record
    try:
        booking = None
        if booking_id:
            booking = Booking.objects.get(id=booking_id)
        
        payment = Payment.objects.create(
            booking=booking,
            amount=amount,
            email=email,
            reference=reference,
            transaction_id=chapa_response["data"]["tx_ref"],
            status="pending",
            chapa_response=chapa_response
        )
        
        # Update booking status if exists
        if booking:
            booking.payment_status = 'pending'
            booking.save()
        
        return JsonResponse({
            "status": "success",
            "message": "Payment initialized successfully.",
            "data": {
                "checkout_url": chapa_response["data"]["checkout_url"],
                "reference": reference,
                "payment_id": payment.id
            }
        })
        
    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def verify_payment(request, reference):
    """
    Verify payment status.
    """
    chapa_response = verify_chapa_transaction(reference)
    
    try:
        payment = Payment.objects.get(reference=reference)
    except Payment.DoesNotExist:
        return JsonResponse(
            {"error": "Payment not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    status_value = chapa_response["data"]["status"]
    
    if status_value == "success":
        payment.status = "completed"
        payment.paid_at = timezone.now()
        payment.chapa_verification_response = chapa_response
        
        # Update associated booking if exists
        if payment.booking:
            booking = payment.booking
            booking.status = 'confirmed'
            booking.payment_status = 'completed'
            booking.paid_at = timezone.now()
            booking.save()
            
            # Send confirmation email
            booking_data = {
                'booking_id': booking.id,
                'confirmation_number': booking.confirmation_number,
                'listing_title': booking.listing.title if hasattr(booking.listing, 'title') else 'Listing',
                'check_in': booking.check_in,
                'check_out': booking.check_out,
                'guests': booking.guests,
                'total_price': booking.total_price,
                'paid_at': booking.paid_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            send_booking_confirmation_email.delay(
                booking_data=booking_data,
                user_email=booking.guest.email
            )
    else:
        payment.status = "failed"
        payment.chapa_verification_response = chapa_response
        
        # Update booking status if exists
        if payment.booking:
            booking = payment.booking
            booking.payment_status = 'failed'
            booking.save()
    
    payment.save()
    
    return JsonResponse({
        "status": payment.status,
        "message": f"Payment {payment.status}",
        "payment_id": payment.id,
        "booking_id": payment.booking.id if payment.booking else None
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history(request):
    """
    Get payment history for the current user.
    """
    payments = Payment.objects.filter(
        Q(email=request.user.email) | Q(booking__guest=request.user)
    ).order_by('-created_at')
    
    data = []
    for payment in payments:
        data.append({
            'id': payment.id,
            'amount': str(payment.amount),
            'status': payment.status,
            'reference': payment.reference,
            'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'paid_at': payment.paid_at.strftime('%Y-%m-%d %H:%M:%S') if payment.paid_at else None,
            'booking_id': payment.booking.id if payment.booking else None,
            'booking_confirmation': payment.booking.confirmation_number if payment.booking else None,
        })
    
    return JsonResponse({"payments": data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_booking_email(request):
    """
    Test endpoint to send booking email (for development only).
    """
    booking_data = {
        'booking_id': 999,
        'confirmation_number': 'TEST123',
        'listing_title': 'Luxury Beach Villa',
        'check_in': '2024-12-25',
        'check_out': '2024-12-30',
        'guests': 2,
        'total_price': 750.00,
        'created_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'confirmed',
    }
    
    # Send test email
    result = send_booking_confirmation_email.delay(
        booking_data=booking_data,
        user_email=request.user.email
    )
    
    return JsonResponse({
        'status': 'success',
        'message': 'Test email sent to your email address.',
        'task_id': result.id
    })