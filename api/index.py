import os
import sys

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sparkzoneproject.wsgi import application

# Auto-apply database migrations on Vercel cold starts
try:
    from django.core.management import call_command
    call_command('migrate', interactive=False)
    
    from sparkzoneapp.models import Game
    if not Game.objects.filter(gpu__isnull=False).exists():
        import seed_data
        seed_data.seed()
except Exception as e:
    print(f"Auto-migration / seed note: {e}")

app = application
