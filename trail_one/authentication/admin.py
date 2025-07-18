from django.contrib import admin
from .models import Users

# Register your models here.
@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'name', 'role', 'email')
    search_fields = ('name', 'email')