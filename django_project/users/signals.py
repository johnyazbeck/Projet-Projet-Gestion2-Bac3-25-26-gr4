from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile

#from stackoverflow https://stackoverflow.com/questions/63962443/create-a-post-save-signal-that-creates-a-profile-object-for-me

# Signal to create a profile when creating a user
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        # Create a profile for the user
        Profile.objects.create(user=instance)

# Signal to save the profile of the user
@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    # user has a profil? save
    if hasattr(instance, 'profile'):  # profile exist?
        instance.profile.save()
