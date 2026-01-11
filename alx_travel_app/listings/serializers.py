from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Listing, Booking, Payment, Review



class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]


class ListingSerializer(serializers.ModelSerializer):
    host = UserInfoSerializer(read_only=True)  # nested host info

    class Meta:
        model = Listing
        fields = [
            "listing_id",
            "host",
            "name",
            "description",
            "country",
            "city",
            "address",
            "price_per_night",
            "created_at",
            "updated_at",
        ]
    
    def validate(self, attrs):
        user = self.context['request'].user
        # Ensure user is a host
        # When connected to the auth service, make sure to use user.role
        if not user.is_staff:
            raise serializers.ValidationError("Only hosts can create listings.")
        
        return attrs
    
    def update(self, instance, validated_data):
        """Only the owner of the listing can update it"""
        user = self.context['request'].user
        if instance.host != user:
            raise serializers.ValidationError("You can only update your own listings.")
        return super().update(instance, validated_data)


class BookingSerializer(serializers.ModelSerializer):
    user = UserInfoSerializer(read_only=True)  # nested guest info
    listing = serializers.PrimaryKeyRelatedField(queryset=Listing.objects.all())

    class Meta:
        model = Booking
        fields = [
            "booking_id",
            "listing",
            "user",
            "start_date",
            "end_date",
            "total_price",
            "status",
            "created_at",
        ]
        read_only_fields = [
            "total_price",
            "booking_id",
            "created_at"
        ]

    def validate(self, attrs):
        start = attrs['start_date']
        end = attrs['end_date']
        listing = attrs['listing']

        # Check availability: if bookings with an overlapping date exist
        overlapping = Booking.objects.filter(
            listing = listing,
            end_date__gte = start,
            start_date__lte = end,
        ).exclude(pk=getattr(self.instance, 'pk', None))  # exclude this current instance

        if overlapping.exists():
            raise serializers.ValidationError("This listing is not available for these dates.")
        
        # Ensure start_date < end_date
        if start > end:
            raise serializers.ValidationError("End date must be after start date.")

        user = self.context['request'].user

        # Ensure user is a guest
        # When connected to the auth service, make sure to use user.role
        if user.is_staff and not self.instance:  # Create: instance is None
            # On update the instance is the object being created (allow host to update its status)
            raise serializers.ValidationError("Staff/hosts cannot create bookings")
        
        return attrs

    def update(self, instance, validated_data):
        user = self.context['request'].user
        if user.is_staff:  # host
            # Only allow host to update the status of a booking
            instance.status = validated_data.get('status', instance.status)
            instance.save()
            return instance
        
        # Guest can update everything except the status, remove it if present
        validated_data.pop('status', None)
        # Put the status of the booking to pending when the guest updates the booking
        # they should wait for the host to cnofirm the date change for ex
        instance.status = "pending"
        return super().update(instance, validated_data)

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "booking_reference",
            "transaction_id",
            "amount",
            "status",
            "created_at",
        ]
        read_only_fields = [
            "transaction_id",
            "created_at",
        ]   

class ReviewSerializer(serializers.ModelSerializer):
    user = UserInfoSerializer(read_only=True)
    listing = ListingSerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            "review_id",
            "listing",
            "user",
            "rating",
            "comment",
            "created_at",
        ]

    def validate(self, attrs):
        if self.context['request'].user.is_staff:
            raise serializers.ValidationError("Only guests can create reviews.")
        return attrs

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        
        return super().create(validated_data)