"""
WSGI config for sparkzoneproject project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sparkzoneproject.settings')

application = get_wsgi_application()

# Auto-initialize SQLite database on Vercel / serverless environments if tables are missing
if os.getenv('VERCEL') == '1' or 'VERCEL' in os.environ or os.path.exists('/var/task'):
    try:
        from django.db import connection
        from django.core.management import call_command
        tables = connection.introspection.table_names()
        if 'sparkzoneapp_category' not in tables:
            call_command('migrate', interactive=False)
            try:
                from seed_data import seed
                seed()
            except Exception as seed_err:
                print(f"Vercel auto-seed notice: {seed_err}")
    except Exception as err:
        print(f"Vercel DB initialization notice: {err}")

