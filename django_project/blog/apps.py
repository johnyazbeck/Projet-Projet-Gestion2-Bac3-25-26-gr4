from django.apps import AppConfig
import os


class BlogConfig(AppConfig):
    name = 'blog'

    def ready(self):
        import blog.signals

        # Prevent APScheduler from running multiple times
        # (Django runserver spawns multiple processes)
        if os.environ.get("RUN_MAIN") != "true":
            return

        from blog.exports.apscheduler import start_safe
        start_safe()
