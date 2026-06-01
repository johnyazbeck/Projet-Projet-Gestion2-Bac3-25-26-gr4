from rest_framework import serializers
from .models import Post, Category, ICTComponent
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import APIKey

class CategoryExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']

class ComponentExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ICTComponent
        fields = ['id', 'name', 'component_type', 'description']

class PostExportSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username')
    categories = CategoryExportSerializer(many=True, read_only=True)
    components = ComponentExportSerializer(many=True, read_only=True)
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'summary', 'problem_description', 'content',
            'author_name', 'date_posted', 'last_modified', 'status',
            'view_count', 'rating', 'useful_count', 'categories', 'components'
        ]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff']

class APIKeySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = APIKey
        fields = [
            'id', 'key', 'name', 'user', 'is_active', 
            'created_at', 'expires_at', 'can_export_posts',
            'can_export_categories', 'can_export_components',
            'rate_limit_per_hour'
        ]
        read_only_fields = ['id', 'key', 'created_at', 'user']

class APIKeyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ['name', 'expires_at', 'can_export_posts', 
                 'can_export_categories', 'can_export_components',
                 'rate_limit_per_hour']