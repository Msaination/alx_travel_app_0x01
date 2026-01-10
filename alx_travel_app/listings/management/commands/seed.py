from django.core.management.base import BaseCommand
from listings.models import Listing
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = "Seed database with sample listings"

    def handle(self, *args, **kwargs):
        host = User.objects.first()
        if not host:
            host = User.objects.create_user(username="host1", password="pass12345")

        sample_data = [
            {
                "host": host,
                "name": "Beach House",
                "description": "Nice house near the beach.",
                "country": "Morocco",
                "city": "Agadir",
                "address": "Beach Road 1",
                "price_per_night": 90,
            },
            {
                "host": host,
                "name": "Mountain Cabin",
                "description": "Cozy cabin with forest view.",
                "country": "Morocco",
                "city": "Ifrane",
                "address": "Pine Street 12",
                "price_per_night": 120,
            },
        ]

        for item in sample_data:
            Listing.objects.create(**item)

        self.stdout.write(self.style.SUCCESS("Database seeded successfully"))