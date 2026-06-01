from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Post, PostHistory

@receiver(pre_save, sender=Post)
def save_post_history(sender, instance, **kwargs):
    # Si nouveau post => pas d'historique
    if not instance.pk:
        return
    
    # Récupérer l’ancienne version
    old_post = Post.objects.get(pk=instance.pk)

    # Si aucun champ important n’a changé → rien sauvegarder
    if (
        old_post.title == instance.title and
        old_post.summary == instance.summary and
        old_post.problem_description == instance.problem_description and
        old_post.content == instance.content and
        old_post.status == instance.status
    ):
        return

    # Sauvegarder l’ancienne version
    PostHistory.objects.create(
        post=old_post,
        modified_by=instance.author,   # ou request.user dans View
        title=old_post.title,
        summary=old_post.summary,
        problem_description=old_post.problem_description,
        content=old_post.content,
        status=old_post.status,
    )
