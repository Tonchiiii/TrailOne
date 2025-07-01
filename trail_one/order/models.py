from django.db import models
from authentication.models import Users  # Import the Users model from the authentication app

class Shipment(models.Model):
    shipment_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(Users, db_column="user_id", on_delete=models.CASCADE)  # Use Users model instead of the default User
    status = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set the timestamp when created
    updated_at = models.DateTimeField(auto_now=True)      # Automatically set the timestamp when updated

    def __str__(self):
        return f"Shipment #{self.shipment_id} - {self.status}"

class ShipmentItem(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='items')  # Removed null=True, blank=True
    description = models.TextField(null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    missing = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set the timestamp when created
    updated_at = models.DateTimeField(auto_now=True)      # Automatically set the timestamp when updated

    def __str__(self):
        return f"Item #{self.id}"
