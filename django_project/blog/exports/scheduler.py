import os
import csv
import json
from django.conf import settings
from django.utils import timezone
from blog.models import Post, ScheduledExport
from blog.serializers import PostExportSerializer

def run_scheduled_exports(frequency):
    """
    Vérifie toutes les minutes si des exports doivent être exécutés
    pour la fréquence donnée (daily, weekly, monthly).
    """
    now = timezone.localtime()
    # Ignorer les secondes et microsecondes pour la comparaison
    current_time = now.replace(second=0, microsecond=0).time()

    # Récupérer tous les exports actifs correspondant à la fréquence et l'heure actuelle
    exports = ScheduledExport.objects.filter(
        frequency=frequency,
        is_active=True,
        execution_time=current_time
    )

    for export in exports:
        execute_export(export)


def execute_export(export):
    """
    Exécute UN export planifié
    """
    posts = Post.objects.all()

    # Appliquer les filtres
    if export.status:
        posts = posts.filter(status=export.status)

    if export.categories.exists():
        posts = posts.filter(categories__in=export.categories.all()).distinct()

    if export.components.exists():
        posts = posts.filter(components__in=export.components.all()).distinct()

    if export.author:
        posts = posts.filter(author=export.author)

    serializer = PostExportSerializer(posts, many=True)
    data = serializer.data

    # Dossier selon la fréquence
    folder = os.path.join(settings.EXPORT_ROOT, export.frequency)
    os.makedirs(folder, exist_ok=True)

    timestamp = timezone.now().strftime("%Y%m%d_%H%M")
    filename = f"{export.name}_{timestamp}.{export.export_format}"
    filepath = os.path.join(folder, filename)

    # Export JSON
    if export.export_format == 'json':
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Export CSV
    elif export.export_format == 'csv':
        if data:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

    export.last_run = timezone.now()    
    export.save()
