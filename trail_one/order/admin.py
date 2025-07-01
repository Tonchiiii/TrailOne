from django.contrib import admin
from .models import Shipment, ShipmentItem

class ShipmentItemInline(admin.TabularInline):
    model = ShipmentItem
    extra = 0  # Number of empty forms to display by default

class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('shipment_id', 'user', 'status', 'created_at', 'updated_at')  # Include created_at and updated_at
    search_fields = ('shipment_id', 'status')  # Searchable fields
    list_filter = ('status',)  # Filter by status
    inlines = [ShipmentItemInline]  # Display ShipmentItems inline within the Shipment form

class ShipmentItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'shipment', 'description', 'quantity', 'missing', 'created_at', 'updated_at')  # Include created_at and updated_at
    search_fields = ('id', 'description')  # Searchable fields

# Register your models with the customized admin
admin.site.register(Shipment, ShipmentAdmin)
admin.site.register(ShipmentItem, ShipmentItemAdmin)
