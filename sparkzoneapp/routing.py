from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/stations/(?P<game_id>\d+)/$', consumers.StationAvailabilityConsumer.as_asgi()),
]
