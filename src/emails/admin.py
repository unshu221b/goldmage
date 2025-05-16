from django.contrib import admin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('clerk_user_id', 'email', 'username', 'account_type', 'is_active', 'is_admin')
    list_filter = ('account_type', 'is_active', 'is_admin')
    search_fields = ('clerk_user_id', 'email', 'username', 'first_name', 'last_name')
    readonly_fields = ('clerk_user_id',)
    fieldsets = (
        ('Clerk Information', {
            'fields': ('clerk_user_id',)
        }),
        ('User Information', {
            'fields': ('username', 'email', 'first_name', 'last_name')
        }),
        ('Account Status', {
            'fields': ('account_type', 'is_active', 'is_admin')
        }),
    )