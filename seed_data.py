import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sparkzoneproject.settings')
django.setup()

from sparkzoneapp.models import Country, State, City, Category, Game

def seed():
    print("Seeding initial location, category, and game data...")
    
    # 1. Country & States & Cities
    india, _ = Country.objects.get_or_create(name="India")
    
    gj, _ = State.objects.get_or_create(country=india, name="Gujarat")
    mh, _ = State.objects.get_or_create(country=india, name="Maharashtra")
    ka, _ = State.objects.get_or_create(country=india, name="Karnataka")

    ahmedabad, _ = City.objects.get_or_create(state=gj, name="Ahmedabad")
    mumbai, _ = City.objects.get_or_create(state=mh, name="Mumbai")
    bengaluru, _ = City.objects.get_or_create(state=ka, name="Bengaluru")

    # 2. Categories
    action, _ = Category.objects.get_or_create(
        categoryName="Action & Adventure",
        defaults={"description": "High-octane action, open-world exploration, and immersive storylines."}
    )
    fps, _ = Category.objects.get_or_create(
        categoryName="FPS & Shooter",
        defaults={"description": "Fast-paced tactical first-person shooters and multiplayer battle arenas."}
    )
    racing, _ = Category.objects.get_or_create(
        categoryName="Racing & Sports",
        defaults={"description": "Supercars, realistic physics, and adrenaline-pumping racing games."}
    )

    # 3. Games
    games_data = [
        {
            "name": "Grand Theft Auto VI",
            "category": action,
            "city": ahmedabad,
            "description": "Experience the ultimate next-gen open world gaming station with RTX 4090 performance.",
            "address": "SparkZone Arena, CG Road, Ahmedabad",
            "pricePerHour": 250.0,
            "totalSystem": 10,
            "availableSystems": 8
        },
        {
            "name": "Cyberpunk 2077: Phantom Liberty",
            "category": action,
            "city": mumbai,
            "description": "Dive into Night City with full Ray Tracing, 4K OLED display, and haptic feedback gear.",
            "address": "SparkZone Hub, Bandra West, Mumbai",
            "pricePerHour": 300.0,
            "totalSystem": 8,
            "availableSystems": 6
        },
        {
            "name": "Valorant Pro Arena",
            "category": fps,
            "city": bengaluru,
            "description": "360Hz Esports monitors, low-latency mechanical keyboards, and 1Gbps fiber gaming line.",
            "address": "SparkZone Lounge, Indiranagar, Bengaluru",
            "pricePerHour": 180.0,
            "totalSystem": 15,
            "availableSystems": 12
        },
        {
            "name": "Forza Horizon 5 Simulator",
            "category": racing,
            "city": ahmedabad,
            "description": "Full motion simulator rig with Fanatec direct drive wheel, pedals, and VR headset.",
            "address": "SparkZone Arena, SG Highway, Ahmedabad",
            "pricePerHour": 350.0,
            "totalSystem": 4,
            "availableSystems": 3
        },
        {
            "name": "Call of Duty: Warzone",
            "category": fps,
            "city": mumbai,
            "description": "Battle royale squad stations equipped with surround sound headsets and 240Hz monitors.",
            "address": "SparkZone Hub, Andheri East, Mumbai",
            "pricePerHour": 220.0,
            "totalSystem": 12,
            "availableSystems": 10
        }
    ]

    for gdata in games_data:
        Game.objects.get_or_create(
            name=gdata["name"],
            defaults=gdata
        )

    print("Seeding completed successfully!")

if __name__ == "__main__":
    seed()
