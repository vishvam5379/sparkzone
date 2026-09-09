import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

class StationAvailabilityConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for live station seat availability and slot status.
    Clients connect to: ws/stations/<game_id>/
    """
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs'].get('game_id')
        self.room_group_name = f"station_{self.game_id}"

        # Join station room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Send initial confirmation
        await self.send_json({
            "type": "connected",
            "game_id": self.game_id,
            "message": f"Connected to live sync for station #{self.game_id}"
        })

    async def disconnect(self, close_code):
        # Leave station room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive_json(self, content, **kwargs):
        """
        Handle incoming messages from client (e.g. ping, request_refresh).
        """
        msg_type = content.get('type')
        if msg_type == 'ping':
            await self.send_json({"type": "pong"})

    async def station_message(self, event):
        """
        Handler for messages broadcasted to group 'station_{game_id}'
        """
        await self.send_json({
            "type": event.get("event", "update"),
            "game_id": event.get("game_id"),
            "data": event.get("data", {})
        })


def broadcast_station_update(game_id, event_type="availability_changed", extra_data=None):
    """
    Synchronous helper to broadcast station & unit status updates to all active WebSockets.
    Can be safely called anywhere from views or signals.
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"station_{game_id}",
                {
                    "type": "station_message",
                    "event": event_type,
                    "game_id": game_id,
                    "data": extra_data or {}
                }
            )
            logger.info(f"Broadcasted {event_type} for station #{game_id}")
    except Exception as e:
        logger.warning(f"WebSocket broadcast skipped/failed for station #{game_id}: {e}")
