from django.core.management.base import BaseCommand
from order.models import Shipment, ShipmentItem
from authentication.models import Users  # Import Users model from authentication app
from random import choice


class Command(BaseCommand):
    help = 'Seed shipments and shipment items'

    def handle(self, *args, **kwargs):
        # Fetch the first user with role 'client' from the authentication app
        client = Users.objects.filter(role='CLIENT').first()

        if not client:
            print("No client found. Please add at least one client.")
            return

        # Sample list of simple item names
        item_names = [
            "Laptop", "Headphones", "Phone Charger", "Notebook", "Pen",
            "Backpack", "Desk Lamp", "USB Cable", "Monitor", "Mouse"
        ]

        # Create 5 shipments for the client
        for i in range(5):
            shipment = Shipment.objects.create(
                user=client,  # Link the shipment to the client
                status=choice(['shipped', 'arrived_at_destination', 'unloading_for_inspection', 'under_review', 'delivered'])  # Random status for shipment
            )

            # Create 5 shipment items for each shipment
            for j in range(5):
                ShipmentItem.objects.create(
                    shipment=shipment,
                    description=choice(item_names),
                    quantity=choice([1, 2, 3, 4, 5]),
                    missing=0  # Setting missing to 0 by default
                )

            self.stdout.write(self.style.SUCCESS(f"Successfully created Shipment #{shipment.shipment_id} with 5 items."))
