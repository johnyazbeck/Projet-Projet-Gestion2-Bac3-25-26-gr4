from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
from django.contrib import messages
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from .models import Post, Category, ICTComponent, Comment, Rating, APIKey, PostHistory, PermissionSystem
from .forms import PostForm, CommentForm, CategoryForm, ComponentForm
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import io
import json
from django.core.serializers import serialize
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.core.cache import cache
import secrets
from .serializers import APIKeySerializer, APIKeyCreateSerializer, UserSerializer, PostExportSerializer, CategoryExportSerializer, ComponentExportSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.core.exceptions import PermissionDenied

from django.db.models import Q, Count


# Décorateur pour vérifier si l'utilisateur est staff/admin
def staff_required(view_func=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.is_staff,
        login_url='blog-home'
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator

# Mixin pour restreindre aux staff uniquement
class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        
        # Superusers and staff always have access
        if user.is_superuser or user.is_staff:
            return True
        
       
        view_name = self.__class__.__name__
        
        if 'Category' in view_name:
            # For category list, check if user has any category permissions
            if view_name == 'CategoryListView':
                return PermissionSystem.objects.filter(user=user).exists()
            
            # For category detail/update/delete, check specific permission
            elif hasattr(self, 'get_object'):
                category = self.get_object()
                permission = PermissionSystem.objects.filter(
                    user=user,
                    category=category
                ).first()
                
                if view_name == 'CategoryUpdateView':
                    return permission and permission.can_edit
                elif view_name == 'CategoryDeleteView':
                    return permission and permission.can_delete
        
        return False
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('blog-home')

def home(request):
    can_add = request.user.is_authenticated
    context = {
        'posts': Post.objects.all(),
        'can_add': can_add
    }
    return render(request, 'blog/home.html', context)

class PostListView(ListView):
    model = Post
    template_name = 'blog/home.html'
    context_object_name = 'posts'
    ordering = ['-date_posted']
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Post.objects.all()
        
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(categories__id=category)
            
        component = self.request.GET.get('component')
        if component:
            queryset = queryset.filter(components__id=component)
            
        search_query = self.request.GET.get('q')
        if search_query:
            keywords = search_query.split()
            query = Q()
            
            for keyword in keywords:
                query |= (
                    Q(title__icontains=keyword) |
                    Q(summary__icontains=keyword) |
                    Q(content__icontains=keyword) |
                    Q(problem_description__icontains=keyword) |
                    Q(categories__name__icontains=keyword) |
                    Q(components__name__icontains=keyword) |
                    Q(author__username__icontains=keyword)
                )
            
            queryset = queryset.filter(query).distinct()
            
        sort = self.request.GET.get('sort')
        if sort == 'views':
            queryset = queryset.order_by('-view_count')
        elif sort == 'rating':
            queryset = queryset.order_by('-rating')
        elif sort == 'newest':
            queryset = queryset.order_by('-date_posted')
        elif sort == 'oldest':
            queryset = queryset.order_by('date_posted')
        else:
            # Par défaut, trier par date (le plus récent en premier)
            queryset = queryset.order_by('-date_posted')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['components'] = ICTComponent.objects.all()
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_component'] = self.request.GET.get('component', '')
        context['selected_sort'] = self.request.GET.get('sort', '')
        
        # Ajouter des statistiques de recherche si besoin
        if context['search_query']:
            context['search_results_count'] = self.get_queryset().count()
        
        return context

class PostDetailView(DetailView):
    model = Post
    
    def get(self, request, *args, **kwargs):
        post = self.get_object()
        post.view_count += 1
        post.save()
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comments.filter(is_active=True).order_by('-created_date')
        context['comment_form'] = CommentForm()
        
        if self.request.user.is_authenticated:
            user_rating = Rating.objects.filter(
                post=self.object, 
                user=self.request.user
            ).first()
            if user_rating:
                context['user_rating'] = user_rating.value
        
        return context
class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['categories'].queryset = Category.objects.all()
        form.fields['components'].queryset = ICTComponent.objects.all()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ensure categories and components are ALWAYS passed to template
        context['categories'] = Category.objects.all()
        context['components'] = ICTComponent.objects.all()
        return context

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        
        # Handle many-to-many fields manually if needed
        self.object = form.save(commit=False)
        self.object.author = self.request.user
        self.object.save()
        form.save_m2m()  # This saves the many-to-many data
        
        return response

    def form_invalid(self, form):
        print("Form errors:", form.errors)  # Debug form errors
        return super().form_invalid(form)

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Ensure the categories queryset is properly set
        form.fields['categories'].queryset = Category.objects.all()
        form.fields['components'].queryset = ICTComponent.objects.all()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Explicitly pass categories and components to template
        context['categories'] = Category.objects.all()
        context['components'] = ICTComponent.objects.all()
        return context

    def form_valid(self, form):
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        return self.request.user.is_superuser or post.author == self.request.user

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = '/'

    def test_func(self):
        post = self.get_object()
        return self.request.user.is_superuser or post.author == self.request.user

# === CATEGORIES VIEWS - ADMIN ONLY ===
class CategoryListView(StaffRequiredMixin, ListView):
    model = Category
    template_name = 'blog/category_list.html'
    context_object_name = 'categories'
    ordering = ['name']
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Category.objects.all()
        
        # Récupérer le paramètre de recherche
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        
        if not self.request.user.is_superuser and not self.request.user.is_staff:
            # Return only categories the user has permission to modify
            queryset = queryset.filter(
                assigned_users__user=self.request.user,
                assigned_users__can_edit=True
            ).distinct()
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['total_posts'] = Post.objects.count()
        
        # Trouver la catégorie la plus utilisée
        categories = Category.objects.all()
        most_used = None
        max_count = 0
        
        for category in categories:
            count = category.post_count()  # Utilise la méthode du modèle
            if count > max_count:
                max_count = count
                most_used = category
        
        context['most_used_category'] = most_used
        
       
        if not self.request.user.is_superuser and not self.request.user.is_staff:
            user_permissions = PermissionSystem.objects.filter(user=self.request.user)
            context['user_category_permissions'] = {
                perm.category_id: {'can_edit': perm.can_edit, 'can_delete': perm.can_delete}
                for perm in user_permissions
            }
        
        return context
    
class CategoryCreateView(StaffRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'blog/category_form.html'
    success_url = reverse_lazy('category-list')
    
    
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Category created successfully!')
        return super().form_valid(form)

class CategoryUpdateView(StaffRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'blog/category_form.html'
    success_url = reverse_lazy('category-list')
    
    
    def test_func(self):
        user = self.request.user
        
        # Superusers and staff can update any category
        if user.is_superuser or user.is_staff:
            return True
        
        # Check if user has permission for this specific category
        category = self.get_object()
        return PermissionSystem.objects.filter(
            user=user,
            category=category,
            can_edit=True
        ).exists()
    
    def form_valid(self, form):
        messages.success(self.request, 'Category updated successfully!')
        return super().form_valid(form)

class CategoryDeleteView(StaffRequiredMixin, DeleteView):
    model = Category
    template_name = 'blog/category_confirm_delete.html'
    success_url = reverse_lazy('category-list')
    
    
    def test_func(self):
        user = self.request.user
        
        # Superusers and staff can delete any category
        if user.is_superuser or user.is_staff:
            return True
        
        # Check if user has delete permission for this specific category
        category = self.get_object()
        return PermissionSystem.objects.filter(
            user=user,
            category=category,
            can_delete=True
        ).exists()
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Category deleted successfully!')
        return super().delete(request, *args, **kwargs)

# === COMPONENTS VIEWS - ADMIN ONLY ===
class ComponentListView(StaffRequiredMixin, ListView):
    model = ICTComponent
    template_name = 'blog/component_list.html'
    context_object_name = 'components'
    ordering = ['name']
    paginate_by = 10
    
    def get_queryset(self):
        # Annotez avec le compte de posts - utilisez 'post' (pas 'post_set')
        queryset = ICTComponent.objects.annotate(
            post_count=Count('post')  # <-- Changé de 'post_set' à 'post'
        )
        
        # Récupérer les paramètres de recherche
        search_query = self.request.GET.get('q')
        component_type = self.request.GET.get('type')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(component_type__icontains=search_query)
            )
        
        if component_type:
            queryset = queryset.filter(component_type=component_type)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiques par type (calculées sur tous les composants, pas seulement ceux filtrés)
        context['server_count'] = ICTComponent.objects.filter(component_type='server').count()
        context['network_count'] = ICTComponent.objects.filter(
            component_type__in=['router', 'modem']
        ).count()
        context['software_count'] = ICTComponent.objects.filter(
            component_type__in=['erp', 'database']
        ).count()
        
        return context

class ComponentCreateView(StaffRequiredMixin, CreateView):
    model = ICTComponent
    form_class = ComponentForm
    template_name = 'blog/component_form.html'
    success_url = reverse_lazy('component-list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Component created successfully!')
        return super().form_valid(form)

class ComponentUpdateView(StaffRequiredMixin, UpdateView):
    model = ICTComponent
    form_class = ComponentForm
    template_name = 'blog/component_form.html'
    success_url = reverse_lazy('component-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Component updated successfully!')
        return super().form_valid(form)

class ComponentDeleteView(StaffRequiredMixin, DeleteView):
    model = ICTComponent
    template_name = 'blog/component_confirm_delete.html'
    success_url = reverse_lazy('component-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Component deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
    return redirect('post-detail', pk=pk)

@login_required
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    post_pk = comment.post.pk
    if request.user == comment.author or request.user.is_superuser:
        comment.delete()
    return redirect('post-detail', pk=post_pk)

@login_required
def rate_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        rating_value = int(request.POST.get('rating'))
        rating, created = Rating.objects.get_or_create(
            post=post,
            user=request.user,
            defaults={'value': rating_value}
        )
        if not created:
            rating.value = rating_value
            rating.save()
        
        ratings = post.ratings.all()
        if ratings:
            post.rating = sum(r.value for r in ratings) / ratings.count()
            post.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'average_rating': round(float(post.rating), 1),
                'total_ratings': ratings.count(),
                'user_rating': rating_value
            })
    
    return redirect('post-detail', pk=pk)

@login_required
def export_posts_csv(request):
    if request.method == 'POST':
        selected_posts = request.POST.get('selected_posts', '')
        
        if selected_posts:
            selected_ids = [int(id.strip()) for id in selected_posts.split(',')]
        else:
            selected_ids = []
            
        posts = Post.objects.filter(id__in=selected_ids)

        response = HttpResponse(content_type='text/csv')
        
        # ===== NOM DU FICHIER AMÉLIORÉ =====
        if len(posts) == 1:
            # Un seul article : utiliser le titre
            post = posts[0]
            # Nettoyer le titre pour le nom de fichier
            clean_title = post.title.replace(' ', '_')
            clean_title = ''.join(c for c in clean_title if c.isalnum() or c in ['_', '-'])
            # Limiter la longueur du nom de fichier
            if len(clean_title) > 50:
                clean_title = clean_title[:50]
            filename = f"{clean_title}_export.csv"
        else:
            # Multiple articles : nom générique avec date
            filename = f"ICT_Knowledge_Base_Export_{timezone.now().strftime('%Y-%m-%d_%H%M')}.csv"
        
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        
        # En-têtes améliorés
        writer.writerow([
            'ID', 'Title', 'Summary', 'Problem Description', 
            'Solution Content', 'Author', 'Date Posted', 
            'Status', 'View Count', 'Rating', 'Useful Count',
            'Categories', 'Components', 'Comment Count',
            'Last Modified'
        ])

        for post in posts:
            writer.writerow([
                post.id,
                post.title,
                post.summary if post.summary and post.summary != "Résumé non spécifié" else "No summary",
                post.problem_description if post.problem_description and post.problem_description != "Problème non spécifié" else "No problem description",
                post.content if post.content else "No solution content",
                post.author.username,
                post.date_posted.strftime('%Y-%m-%d %H:%M'),
                post.get_status_display(),
                post.view_count,
                f"{post.rating:.1f}" if post.rating else "0.0",
                post.useful_count,
                ', '.join([cat.name for cat in post.categories.all()]),
                ', '.join([comp.name for comp in post.components.all()]),
                post.comments.count(),
                post.last_modified.strftime('%Y-%m-%d %H:%M') if post.last_modified else ""
            ])

        return response
    return redirect('blog-home')


@login_required
def export_posts_pdf(request):
    if request.method == 'POST':
        selected_posts = request.POST.get('selected_posts', '')
        
        if selected_posts:
            selected_ids = [int(id.strip()) for id in selected_posts.split(',')]
        else:
            selected_ids = []
            
        posts = Post.objects.filter(id__in=selected_ids)

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        
        width, height = letter
        y_position = height - 50
        line_height = 14
        margin = 50
        
        # ===== PAGE D'ACCUEIL (si export multiple) =====
        if len(posts) > 1:
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawCentredString(width/2, height - 100, "ICT Knowledge Base - Articles Export")
            
            pdf.setFont("Helvetica", 12)
            pdf.drawCentredString(width/2, height - 130, f"Export Date: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
            pdf.drawCentredString(width/2, height - 150, f"Total Articles: {len(posts)}")
            
            # Liste des articles
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(margin, height - 200, "Table of Contents:")
            y_position = height - 220
            
            pdf.setFont("Helvetica", 12)
            for i, post in enumerate(posts, 1):
                title = post.title
                # Tronquer les titres trop longs
                if len(title) > 60:
                    title = title[:57] + "..."
                pdf.drawString(margin + 20, y_position, f"{i}. {title}")
                y_position -= line_height + 5
                
                if y_position < 100:
                    pdf.showPage()
                    y_position = height - 50
            
            pdf.showPage()
            y_position = height - 50
        
        # ===== CONTENU DES ARTICLES =====
        for post_index, post in enumerate(posts, 1):
            if post_index > 1:
                pdf.showPage()
                y_position = height - 50
            
            # ===== TITRE DE L'ARTICLE (CENTRÉ, GRAND) =====
            pdf.setFont("Helvetica-Bold", 20)
            title = post.title
            
            # Découper le titre en plusieurs lignes si trop long
            title_words = title.split()
            title_lines = []
            current_line = ""
            
            for word in title_words:
                if len(current_line) + len(word) + 1 <= 60:  # ~60 caractères par ligne
                    current_line = f"{current_line} {word}".strip() if current_line else word
                else:
                    title_lines.append(current_line)
                    current_line = word
            if current_line:
                title_lines.append(current_line)
            
            # Centrer chaque ligne
            start_y = height - 80
            for line in title_lines:
                pdf.drawCentredString(width/2, start_y, line)
                start_y -= 25
            
            y_position = start_y - 20
            
            # ===== MÉTADONNÉES (en colonnes) =====
            pdf.setFont("Helvetica", 10)
            pdf.setFillColorRGB(0.3, 0.3, 0.3)  # Gris foncé
            
            # Colonne gauche
            left_info = [
                f"Author: {post.author.username}",
                f"Date: {post.date_posted.strftime('%Y-%m-%d')}",
                f"Status: {post.get_status_display()}"
            ]
            
            # Colonne droite
            right_info = [
                f"Views: {post.view_count}",
                f"Rating: {post.rating:.1f}/5" if post.rating else "Rating: N/A",
                f"Useful votes: {post.useful_count}"
            ]
            
            # Afficher les deux colonnes
            for i, (left, right) in enumerate(zip(left_info, right_info)):
                pdf.drawString(margin, y_position, left)
                pdf.drawString(width - margin - 150, y_position, right)
                y_position -= 15
            
            # Ligne de séparation
            y_position -= 10
            pdf.setStrokeColorRGB(0.8, 0.8, 0.8)
            pdf.line(margin, y_position, width - margin, y_position)
            y_position -= 20
            
            # ===== CATÉGORIES ET COMPOSANTS =====
            categories = post.categories.all()
            components = post.components.all()
            
            if categories:
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(margin, y_position, "Categories:")
                pdf.setFont("Helvetica", 10)
                category_names = ", ".join([cat.name for cat in categories])
                
                # Justifier le texte
                category_lines = []
                words = category_names.split()
                current_line = ""
                for word in words:
                    if len(current_line + " " + word) <= 80:
                        current_line = f"{current_line} {word}".strip() if current_line else word
                    else:
                        category_lines.append(current_line)
                        current_line = word
                if current_line:
                    category_lines.append(current_line)
                
                for line in category_lines:
                    pdf.drawString(margin + 10, y_position - 15, line)
                    y_position -= 15
                y_position -= 10
            
            if components:
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(margin, y_position, "ICT Components:")
                pdf.setFont("Helvetica", 10)
                component_names = ", ".join([comp.name for comp in components])
                
                # Justifier le texte
                component_lines = []
                words = component_names.split()
                current_line = ""
                for word in words:
                    if len(current_line + " " + word) <= 80:
                        current_line = f"{current_line} {word}".strip() if current_line else word
                    else:
                        component_lines.append(current_line)
                        current_line = word
                if current_line:
                    component_lines.append(current_line)
                
                for line in component_lines:
                    pdf.drawString(margin + 10, y_position - 15, line)
                    y_position -= 15
                y_position -= 20
            
            # ===== RÉSUMÉ =====
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(margin, y_position, "Summary")
            y_position -= 20
            
            pdf.setFont("Helvetica", 11)
            if post.summary and post.summary.strip() and post.summary != "Résumé non spécifié":
                summary_text = post.summary
            else:
                summary_text = "No summary provided"
            
            summary_lines = justify_text(summary_text, width - 2*margin, pdf, "Helvetica", 11)
            
            for line in summary_lines:
                if y_position < 100:
                    pdf.showPage()
                    y_position = height - 50
                    pdf.setFont("Helvetica", 11)
                pdf.drawString(margin, y_position, line)
                y_position -= line_height
            y_position -= 10
            
            # ===== DESCRIPTION DU PROBLÈME =====
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(margin, y_position, "Problem Description")
            y_position -= 20
            
            pdf.setFont("Helvetica", 11)
            if post.problem_description and post.problem_description.strip() and post.problem_description != "Problème non spécifié":
                problem_text = post.problem_description
            else:
                problem_text = "No problem description provided"
            
            problem_lines = justify_text(problem_text, width - 2*margin, pdf, "Helvetica", 11)
            
            for line in problem_lines:
                if y_position < 100:
                    pdf.showPage()
                    y_position = height - 50
                    pdf.setFont("Helvetica", 11)
                pdf.drawString(margin, y_position, line)
                y_position -= line_height
            y_position -= 10
            
            # ===== SOLUTION (LE CONTENU PRINCIPAL) =====
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(margin, y_position, "Solution and Resolution")
            y_position -= 20
            
            pdf.setFont("Helvetica", 11)
            if post.content and post.content.strip():
                content_text = post.content
            else:
                content_text = "No solution content provided"
            
            content_lines = justify_text(content_text, width - 2*margin, pdf, "Helvetica", 11)
            
            for line in content_lines:
                if y_position < 100:
                    pdf.showPage()
                    y_position = height - 50
                    pdf.setFont("Helvetica", 11)
                pdf.drawString(margin, y_position, line)
                y_position -= line_height
            
            # ===== FOOTER =====
            pdf.setFont("Helvetica", 8)
            pdf.setFillColorRGB(0.5, 0.5, 0.5)
            pdf.drawCentredString(width/2, 30, f"Page {post_index} of {len(posts)} - ICT Knowledge Base")
            pdf.drawCentredString(width/2, 20, f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}")
        
        pdf.save()
        buffer.seek(0)
        
        # Nom du fichier basé sur le premier article
        if posts:
            filename = f"{posts[0].title.replace(' ', '_')}.pdf"
            if len(posts) > 1:
                filename = f"ICT_Articles_Export_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
        else:
            filename = "export.pdf"
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    return redirect('blog-home')


# ===== FONCTION POUR JUSTIFIER LE TEXTE =====
def justify_text(text, max_width, pdf, font_name, font_size):
    """
    Fonction pour justifier le texte dans le PDF
    """
    pdf.setFont(font_name, font_size)
    
    # Nettoyer le texte HTML si présent
    import re
    text = re.sub(r'<[^>]+>', '', text)  # Enlever les balises HTML
    text = re.sub(r'\s+', ' ', text)      # Remplacer les espaces multiples
    
    words = text.split()
    lines = []
    current_line = []
    current_width = 0
    
    for word in words:
        word_width = pdf.stringWidth(word, font_name, font_size)
        
        if current_width + word_width + (len(current_line) * pdf.stringWidth(' ', font_name, font_size)) <= max_width:
            current_line.append(word)
            current_width += word_width
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_width = word_width
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Justifier chaque ligne (sauf la dernière)
    justified_lines = []
    for i, line in enumerate(lines):
        if i == len(lines) - 1:
            justified_lines.append(line)  # Ne pas justifier la dernière ligne
        else:
            words_in_line = line.split()
            if len(words_in_line) > 1:
                total_width = pdf.stringWidth(line, font_name, font_size)
                space_to_distribute = max_width - total_width
                spaces_between_words = len(words_in_line) - 1
                
                if spaces_between_words > 0:
                    extra_space_per_gap = space_to_distribute / spaces_between_words
                    justified_line = ""
                    
                    for j, word in enumerate(words_in_line):
                        justified_line += word
                        if j < spaces_between_words:
                            # Ajouter l'espace normal + l'espace supplémentaire
                            normal_space = pdf.stringWidth(' ', font_name, font_size)
                            extra_spaces = int((extra_space_per_gap / normal_space) * 10)
                            justified_line += ' ' * (1 + extra_spaces // 10)
                    
                    justified_lines.append(justified_line)
                else:
                    justified_lines.append(line)
            else:
                justified_lines.append(line)
    
    return justified_lines
@login_required
def export_posts_json(request):
    if request.method == 'POST':
        selected_posts = request.POST.get('selected_posts', '')
        
        if selected_posts:
            selected_ids = [int(id.strip()) for id in selected_posts.split(',')]
        else:
            selected_ids = []
            
        posts = Post.objects.filter(id__in=selected_ids)

        # Préparer les données pour l'export JSON
        posts_data = []
        for post in posts:
            post_data = {
                'article_id': post.id,
                'title': post.title,
                'summary': post.summary if post.summary and post.summary != "Résumé non spécifié" else "No summary provided",
                'problem_description': post.problem_description if post.problem_description and post.problem_description != "Problème non spécifié" else "No problem description provided",
                'content': post.content if post.content else "No solution content provided",
                'author': post.author.username,
                'date_posted': post.date_posted.strftime('%Y-%m-%d %H:%M'),
                'status': post.get_status_display(),
                'view_count': post.view_count,
                'rating': float(post.rating) if post.rating else 0.0,
                'useful_count': post.useful_count,
                'categories': [category.name for category in post.categories.all()],
                'components': [component.name for component in post.components.all()],
                'comment_count': post.comments.count()
            }
            posts_data.append(post_data)

        # Créer la réponse JSON avec séparation visuelle
        response_data = {
            'export_info': {
                'export_date': timezone.now().strftime('%Y-%m-%d %H:%M'),
                'total_articles': len(posts),
                'format': 'JSON',
                'version': '1.0'
            },
            'articles': posts_data
        }

        # Convertir en JSON avec un formatage amélioré
        json_output = json.dumps(response_data, indent=2, ensure_ascii=False)
        
        # Ajouter des séparateurs visuels entre les articles
        json_lines = json_output.split('\n')
        formatted_json = []
        
        in_articles_array = False
        article_count = 0
        
        for line in json_lines:
            formatted_json.append(line)
            
            # Détecter le début du tableau d'articles
            if '"articles": [' in line:
                in_articles_array = True
                article_count = 0
            
            # Ajouter une ligne de séparation après chaque article (sauf le dernier)
            if in_articles_array and '},' in line:
                article_count += 1
                if article_count < len(posts_data):
                    formatted_json.append('')  # Ligne vide
                    formatted_json.append('    ' + '_' * 120)  # Ligne de séparation normale
                    formatted_json.append('')  # Ligne vide
        
        # Rejoindre les lignes formatées
        final_json = '\n'.join(formatted_json)
        
        # ===== NOM DU FICHIER AMÉLIORÉ =====
        if len(posts) == 1:
            # Un seul article : utiliser le titre
            post = posts[0]
            # Nettoyer le titre pour le nom de fichier
            clean_title = post.title.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_')
            clean_title = ''.join(c for c in clean_title if c.isalnum() or c in ['_', '-'])
            filename = f"{clean_title}_export.json"
        else:
            # Multiple articles : nom générique avec date
            filename = f"ICT_Knowledge_Base_Export_{timezone.now().strftime('%Y-%m-%d_%H%M')}.json"
        
        response = HttpResponse(final_json, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    return redirect('blog-home')

def about(request):
    return render(request, 'blog/about.html', {'title': 'About'})

 #Afficher une ancienne version d'article
def post_history_view(request, pk):
    history = get_object_or_404(PostHistory, pk=pk)
    return render(request, "blog/post_history_detail.html", {"history": history})

# =============================================================================
# API ENDPOINTS FOR EXPORT
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_export_posts(request):
    """
    API endpoint pour exporter les articles en JSON ou CSV
    Exemple: /api/export/posts/?format=json&status=published
    """
    export_format = request.GET.get('format', 'json').lower()
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    component_filter = request.GET.get('component')
    author_filter = request.GET.get('author')
    
    # Filtrer les posts
    posts = Post.objects.all()
    
    if status_filter:
        posts = posts.filter(status=status_filter)
    
    if category_filter:
        posts = posts.filter(categories__id=category_filter)
    
    if component_filter:
        posts = posts.filter(components__id=component_filter)
    
    if author_filter:
        posts = posts.filter(author__username=author_filter)
    
    # Sérialiser les données
    serializer = PostExportSerializer(posts, many=True)
    data = serializer.data
    
    if export_format == 'csv':
        return export_to_csv_api(data)
    else:
        return export_to_json_api(data)

def export_to_csv_api(data):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="posts_api_export.csv"'
    
    writer = csv.writer(response)
    
    # En-têtes basés sur les champs sérialisés
    if data:
        headers = data[0].keys()
        writer.writerow(headers)
        
        for item in data:
            writer.writerow([str(value) for value in item.values()])
    
    return response

def export_to_json_api(data):
    response_data = {
        'metadata': {
            'export_date': timezone.now().isoformat(),
            'total_posts': len(data),
            'format': 'JSON',
            'version': '1.0'
        },
        'posts': data
    }
    
    response = HttpResponse(
        json.dumps(response_data, indent=2, ensure_ascii=False),
        content_type='application/json'
    )
    response['Content-Disposition'] = 'attachment; filename="posts_api_export.json"'
    return response

@api_view(['GET'])
@permission_classes([IsAdminUser])  # Changé : admin seulement
def api_export_categories(request):
    """
    API endpoint pour exporter les catégories
    """
    categories = Category.objects.all()
    serializer = CategoryExportSerializer(categories, many=True)
    
    response_data = {
        'metadata': {
            'export_date': timezone.now().isoformat(),
            'total_categories': len(categories),
            'format': 'JSON'
        },
        'categories': serializer.data
    }
    
    return Response(response_data)

@api_view(['GET'])
@permission_classes([IsAdminUser])  # Changé : admin seulement
def api_export_components(request):
    """
    API endpoint pour exporter les composants ICT
    """
    components = ICTComponent.objects.all()
    serializer = ComponentExportSerializer(components, many=True)
    
    response_data = {
        'metadata': {
            'export_date': timezone.now().isoformat(),
            'total_components': len(components),
            'format': 'JSON'
        },
        'components': serializer.data
    }
    
    return Response(response_data)


# =============================================================================
# API AUTHENTICATION & ACCESS CONTROL - RESTAURÉ
# =============================================================================

class APIKeyListView(LoginRequiredMixin, generics.ListCreateAPIView):
    """
    Liste et création des clés API
    """
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return APIKey.objects.all()
        return APIKey.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return APIKeyCreateSerializer
        return APIKeySerializer
    
    def perform_create(self, serializer):
        # Générer une clé API sécurisée
        api_key = secrets.token_urlsafe(32)
        serializer.save(user=self.request.user, key=api_key)
        
        # Log de création
        print(f"API Key created for user {self.request.user.username}: {api_key}")

class APIKeyDetailView(LoginRequiredMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Détail, modification et suppression des clés API
    """
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return APIKey.objects.all()
        return APIKey.objects.filter(user=self.request.user)

class UserProfileView(LoginRequiredMixin, generics.RetrieveAPIView):
    """
    Profil utilisateur avec informations API
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

# Custom Permission Classes
class HasExportPermission(permissions.BasePermission):
    """
    Permission personnalisée pour l'export
    """
    def has_permission(self, request, view):
        # Vérifier si l'utilisateur est authentifié
        if not request.user.is_authenticated:
            return False
        
        # Les admins ont tous les droits
        if request.user.is_staff:
            return True
        
        # Vérifier les permissions spécifiques
        if view.action == 'api_export_posts':
            return getattr(request.user, 'can_export', False) or request.user.is_staff
        elif view.action == 'api_export_categories':
            return getattr(request.user, 'can_export_categories', False) or request.user.is_staff
        elif view.action == 'api_export_components':
            return getattr(request.user, 'can_export_components', False) or request.user.is_staff
        
        return False

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission pour les propriétaires ou admins
    """
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.user == request.user

# Rate Limiting Decorator
def rate_limit(key_prefix, limit, window):
    """
    Décorateur pour limiter le taux d'accès
    """
    def decorator(view_func):
        def wrapped(request, *args, **kwargs):
            if request.user.is_authenticated:
                cache_key = f"{key_prefix}_{request.user.id}"
                count = cache.get(cache_key, 0)
                
                if count >= limit:
                    return Response(
                        {'error': 'Rate limit exceeded. Try again later.'},
                        status=status.HTTP_429_TOO_MANY_REQUESTS
                    )
                
                cache.set(cache_key, count + 1, window)
            
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator

# =============================================================================
# JWT AUTHENTICATION ENDPOINTS - RESTAURÉ
# =============================================================================

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Endpoint pour obtenir un token JWT
    """
    pass

class CustomTokenRefreshView(TokenRefreshView):
    """
    Endpoint pour rafraîchir un token JWT
    """
    pass
