from django.urls import path
from .views import (
    PostListView,
    PostDetailView,
    PostCreateView,
    PostUpdateView,
    PostDeleteView,
    CategoryListView,
    CategoryCreateView,
    CategoryUpdateView,
    CategoryDeleteView,
    ComponentListView,
    ComponentCreateView,
    ComponentUpdateView,
    ComponentDeleteView,
    add_comment,
    delete_comment,
    rate_post,
    export_posts_csv,
    export_posts_pdf,
    export_posts_json,
    about,
   
    post_history_view,
    # API Views
    api_export_posts,
    api_export_categories,
    api_export_components,
    APIKeyListView,
    APIKeyDetailView,
    UserProfileView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView
)

urlpatterns = [
    # Post URLs
    path('', PostListView.as_view(), name='blog-home'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('post/new/', PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/update/', PostUpdateView.as_view(), name='post-update'),
    path('post/<int:pk>/delete/', PostDeleteView.as_view(), name='post-delete'),
    
    # Category Management URLs
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/new/', CategoryCreateView.as_view(), name='category-create'),
    path('categories/<int:pk>/update/', CategoryUpdateView.as_view(), name='category-update'),
    path('categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category-delete'),
    # SUPPRIMER cette ligne : path('category/quick-add/', quick_add_category, name='quick_add_category'),
    
    # Component Management URLs
    path('components/', ComponentListView.as_view(), name='component-list'),
    path('components/new/', ComponentCreateView.as_view(), name='component-create'),
    path('components/<int:pk>/update/', ComponentUpdateView.as_view(), name='component-update'),
    path('components/<int:pk>/delete/', ComponentDeleteView.as_view(), name='component-delete'),
    # SUPPRIMER cette ligne : path('component/quick-add/', quick_add_component, name='quick_add_component'),
    
    # Comment and Rating URLs
    path('post/<int:pk>/comment/', add_comment, name='add-comment'),
    path('comment/<int:pk>/delete/', delete_comment, name='delete-comment'),
    path('post/<int:pk>/rate/', rate_post, name='rate-post'),
    
    # Export and About URLs
    path('export-posts-csv/', export_posts_csv, name='export-posts-csv'),
    path('export-posts-pdf/', export_posts_pdf, name='export-posts-pdf'),
    path('export-posts-json/', export_posts_json, name='export-posts-json'),
    path('about/', about, name='blog-about'),
    
    # History of Articles
    path("post/history/<int:pk>/", post_history_view, name="post-history-view"),

    # API Endpoints for Export
    path('api/export/posts/', api_export_posts, name='api-export-posts'),
    path('api/export/categories/', api_export_categories, name='api-export-categories'),
    path('api/export/components/', api_export_components, name='api-export-components'),

    # API Authentication & Management URLs
    path('api/auth/profile/', UserProfileView.as_view(), name='api-user-profile'),
    path('api/keys/', APIKeyListView.as_view(), name='api-key-list'),
    path('api/keys/<int:pk>/', APIKeyDetailView.as_view(), name='api-key-detail'),

    # JWT Authentication endpoints
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
]