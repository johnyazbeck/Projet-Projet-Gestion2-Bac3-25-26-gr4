from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'image')  # Display user and image in the list view
    search_fields = ('user__username',)  # Allow searching by username
    list_filter = ('user',)  # Add filter options by user
    ordering = ('user',)  # Order profiles by user