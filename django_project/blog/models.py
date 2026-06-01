from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from ckeditor.fields import RichTextField


# ============================================================
#                    MODELS ORIGINELS
# ============================================================

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name

    def post_count(self):
        return self.post_set.count()
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']


class ICTComponent(models.Model):
    TYPE_CHOICES = [
        ('server', 'Server'),
        ('erp', 'ERP System'),
        ('database', 'Database Server'),
        ('modem', 'Modem'),
        ('router', 'Router'),
        ('others', 'Others'),
    ]

    name = models.CharField(max_length=100)
    component_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='others')
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

    def post_count(self):
        return self.post_set.count()
    
    class Meta:
        ordering = ['name']


class Post(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
   #title is required 
    title = models.CharField(max_length=200)
    #not required fields
    summary = RichTextField(config_name='default', blank=True, null=True)
    problem_description = RichTextField(config_name='default', blank=True, null=True)
    content = RichTextField(config_name='default', blank=True, null=True)
    # Status with default and optional
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='draft',
        blank=True  # Make this optional too
    )
    date_posted = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
   
    categories = models.ManyToManyField(Category, blank=True)
    components = models.ManyToManyField(ICTComponent, blank=True)

    view_count = models.IntegerField(default=0)
    rating = models.FloatField(default=0)
    useful_count = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.pk})


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_solution = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_date']

    def __str__(self):
        return f'Comment by {self.author} on {self.post.title}'

    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.post.pk})


class Rating(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'user']

    def __str__(self):
        return f'Rating {self.value} by {self.user} for {self.post.title}'


class PostHistory(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='history')
    modified_by = models.ForeignKey(User, on_delete=models.CASCADE)
    modified_date = models.DateTimeField(auto_now_add=True)
    change_reason = models.TextField(blank=True, default="")

    # Snapshot complet
    title = models.CharField(max_length=200, default="")
    summary = RichTextField(config_name='default', default="")
    problem_description = RichTextField(config_name='default', default="")
    content = RichTextField(config_name='default', default="")
    status = models.CharField(max_length=10, default="draft")

    def __str__(self):
        return f'History for {self.post.title} ({self.modified_date})'


class UsefulVote(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='useful_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'user']

    def __str__(self):
        return f'Useful vote by {self.user} for {self.post.title}'


class APIKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Permissions
    can_export_posts = models.BooleanField(default=True)
    can_export_categories = models.BooleanField(default=True)
    can_export_components = models.BooleanField(default=True)
    
    # Limitations
    rate_limit_per_hour = models.IntegerField(default=100)
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"



# ============================================================
#        NOUVEAU SYSTEME DE PERMISSIONS : PermissionSystem
# ============================================================

class PermissionSystem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permission_systems')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='assigned_users')
    can_edit = models.BooleanField(default=True)
    can_delete = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_permission_systems'
    )

    def __str__(self):
        return f"{self.user.username} -> {self.category.name}"

    class Meta:
        unique_together = ['user', 'category']
        verbose_name = "Permission System"
        verbose_name_plural = "Permission Systems"


# ============================================================
#              FONCTIONS DE ROLE ATTACHEES À USER
# ============================================================

def user_has_category_permission(user, category):
    """Check if user can modify a specific category"""
    if user.is_superuser or user.is_staff:
        return True
    
    return PermissionSystem.objects.filter(
        user=user,
        category=category,
        can_edit=True
    ).exists()


def get_user_categories(user):
    """Get all categories a user can modify"""
    if user.is_superuser or user.is_staff:
        return Category.objects.all()
    
    return Category.objects.filter(
        assigned_users__user=user,
        assigned_users__can_edit=True
    ).distinct()


# Patch des méthodes dans User model
User.add_to_class('has_category_permission', staticmethod(user_has_category_permission))
User.add_to_class('get_allowed_categories', staticmethod(get_user_categories))

class ScheduledExport(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    FORMAT_CHOICES = [
        ('json', 'JSON'),
        ('csv', 'CSV'),
    ]

    STATUS_CHOICES = Post.STATUS_CHOICES  # reprend exactement les mêmes choix que Post

    name = models.CharField(max_length=100)

    # Qui a créé la tâche
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='scheduled_exports_created'
    )

    # Fréquence
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)

    # Heure d’exécution
    execution_time = models.TimeField()

    # Format d’export
    export_format = models.CharField(max_length=10, choices=FORMAT_CHOICES)

    # Filtres (choix depuis la base)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        blank=True
    )
    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name='scheduled_exports'
    )
    components = models.ManyToManyField(
        ICTComponent,
        blank=True,
        related_name='scheduled_exports'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduled_exports_authored'
    )

    # Actif / inactif
    is_active = models.BooleanField(default=True)

    last_run = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Forcer secondes et microsecondes à 0 pour execution_time."""
        if self.execution_time:
            self.execution_time = self.execution_time.replace(second=0, microsecond=0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.frequency})"