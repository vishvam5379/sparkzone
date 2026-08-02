import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sparkzoneproject.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@sparkzone.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Admin@1234')

if not User.objects.filter(username=username).exists():
    print(f"Creating superuser '{username}'...")
    User.objects.create_superuser(username=username, email=email, password=password)
    print("Superuser created successfully!")
else:
    print(f"Updating password for existing superuser '{username}'...")
    user = User.objects.get(username=username)
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print("Superuser password updated successfully!")

