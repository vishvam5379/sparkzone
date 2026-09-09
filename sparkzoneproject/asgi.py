import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sparkzoneproject.settings')

# Initialize Django ASGI application early to ensure the AppRegistry is populated
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import sparkzoneapp.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            sparkzoneapp.routing.websocket_urlpatterns
        )
    ),
})
