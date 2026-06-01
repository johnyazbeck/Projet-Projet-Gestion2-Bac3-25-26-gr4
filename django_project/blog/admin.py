from django.contrib import admin
from .models import Category, ICTComponent, Post, Comment, Rating, PostHistory, UsefulVote
from .models import APIKey

from .models import PermissionSystem,ScheduledExport       
from django.contrib.auth.models import User



@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_by', 'created_at', 'post_count', 'assigned_users_count')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)
    
    def post_count(self, obj):
        return obj.post_set.count()
    post_count.short_description = "Number of articles"
    
    def assigned_users_count(self, obj):
        return obj.assigned_users.count()
    assigned_users_count.short_description = "Assigned Users"

@admin.register(ICTComponent)
class ICTComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'component_type', 'description', 'created_by', 'created_at', 'post_count')
    list_filter = ('component_type', 'created_at')
    search_fields = ('name', 'description')
    
    def post_count(self, obj):
        return obj.post_set.count()
    post_count.short_description = "Number of articles"

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('author', 'created_date')

class RatingInline(admin.TabularInline):
    model = Rating
    extra = 0
    readonly_fields = ('user', 'created_date')

class PostHistoryInline(admin.TabularInline):
    model = PostHistory
    extra = 0
    readonly_fields = ('modified_by', 'modified_date', 'change_reason')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'date_posted', 'view_count', 'rating')
    list_filter = ('status', 'categories', 'date_posted')
    search_fields = ('title', 'summary', 'problem_description', 'content')
    readonly_fields = ('date_posted', 'last_modified', 'view_count', 'rating', 'useful_count')
    filter_horizontal = ('categories', 'components')
    inlines = [CommentInline, RatingInline, PostHistoryInline]
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('title', 'summary', 'problem_description', 'content')
        }),
        ('Classification et métadonnées', {
            'fields': ('author', 'status', 'categories', 'components')
        }),
        ('Statistiques (automatiques)', {
            'fields': ('view_count', 'rating', 'useful_count', 'date_posted', 'last_modified'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('categories', 'components')

    def has_add_permission(self, request):
        return request.user.is_authenticated

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return False
        return obj.author == request.user

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return False
        return obj.author == request.user

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'created_date', 'is_solution', 'is_active')
    list_filter = ('is_solution', 'is_active', 'created_date')
    search_fields = ('content', 'post__title', 'author__username')
    list_editable = ('is_solution', 'is_active')

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'value', 'created_date')
    list_filter = ('value', 'created_date')
    search_fields = ('post__title', 'user__username')

@admin.register(PostHistory)
class PostHistoryAdmin(admin.ModelAdmin):
    list_display = ('post', 'modified_by', 'modified_date')
    list_filter = ('modified_date',)
    search_fields = ('post__title', 'modified_by__username')

@admin.register(UsefulVote)
class UsefulVoteAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'created_date')
    list_filter = ('created_date',)
    search_fields = ('post__title', 'user__username')

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_active', 'created_at', 'expires_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'user__username', 'key']
    readonly_fields = ['key', 'created_at']


@admin.register(PermissionSystem)
class PermissionSystemAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'can_edit', 'can_delete', 'created_by', 'created_at')
    list_filter = ('can_edit', 'can_delete', 'created_at', 'category')
    search_fields = ('user__username', 'user__email', 'category__name')
    list_editable = ('can_edit', 'can_delete')
    
    # Fields for the add form (without created_at)
    add_fieldsets = (
        ('User and Category', {
            'fields': ('user', 'category')
        }),
        ('Permissions', {
            'fields': ('can_edit', 'can_delete')
        }),
    )
    
    # Fields for the change form (with read-only metadata)
    fieldsets = (
        ('User and Category', {
            'fields': ('user', 'category')
        }),
        ('Permissions', {
            'fields': ('can_edit', 'can_delete')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Make created_at read-only in change form
    readonly_fields = ('created_at', 'created_by')
    
    def get_fieldsets(self, request, obj=None):
        if obj:  # Editing existing object
            return self.fieldsets
        else:  # Adding new object
            return self.add_fieldsets
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ('user', 'category')
        else:  # Adding new object
            return self.readonly_fields
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # If creating new
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Filter users for better selection
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(is_staff=False, is_superuser=False).order_by('username')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    
@admin.register(ScheduledExport)
class ScheduledExportAdmin(admin.ModelAdmin):
    list_display = ('name', 'frequency', 'export_format', 'is_active', 'last_run')
    list_filter = ('frequency', 'export_format', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('last_run',)
    exclude = ('created_by',)

    # Utiliser le filter_horizontal comme dans PostAdmin
    filter_horizontal = ('categories', 'components')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
