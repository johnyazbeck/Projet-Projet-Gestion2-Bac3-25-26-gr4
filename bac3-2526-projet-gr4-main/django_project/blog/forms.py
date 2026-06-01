from django import forms
from .models import Post, Category, ICTComponent, Comment
from ckeditor.widgets import CKEditorWidget  # IMPORTANT : Ajout de CKEditor

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter category description (optional)'
            }),
        }
        labels = {
            'name': 'Category Name',
            'description': 'Description',
        }

class ComponentForm(forms.ModelForm):
    class Meta:
        model = ICTComponent
        fields = ['name', 'component_type', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter component name'
            }),
            'component_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter component description (optional)'
            }),
        }
        labels = {
            'name': 'Component Name',
            'component_type': 'Component Type',
            'description': 'Description',
        }

class PostForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'style': 'display: none;'
        }),
        required=False,
        label="Technical Categories"
    )
    
    components = forms.ModelMultipleChoiceField(
        queryset=ICTComponent.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'style': 'display: none;'
        }),
        required=False,
        label="ICT Components"
    )

    class Meta:
        model = Post
        fields = [
            'title',
            'summary',
            'problem_description',
            'content',
            'status',
            'categories',
            'components'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            # REMPLACER par CKEditorWidget SANS upload
            'summary': CKEditorWidget(config_name='default'),
            'problem_description': CKEditorWidget(config_name='default'),
            'content': CKEditorWidget(config_name='default'),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'summary': 'Article',
            'problem_description': 'Detailed Problem Description',
            'content': 'Solution and Resolution',
        }


    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        # Make all fields except title optional
        self.fields['summary'].required = False
        self.fields['problem_description'].required = False
        self.fields['content'].required = False
        self.fields['status'].required = False
        
        # Set default value for status if creating new post
        if not self.instance.pk:
            self.fields['status'].initial = 'draft'

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Add your comment here...',
                'class': 'form-control'
            }),
        }
        labels = {
            'content': ''
        }