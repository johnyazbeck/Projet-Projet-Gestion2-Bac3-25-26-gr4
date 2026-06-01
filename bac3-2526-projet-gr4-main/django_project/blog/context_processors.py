def can_add_article(request):
    if request.user.is_authenticated:
        can_add = True  # Tout utilisateur authentifié peut ajouter
    else:
        can_add = False
    return {'can_add': can_add}