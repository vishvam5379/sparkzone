import os
import django
import hashlib

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sparkzoneproject.settings')
django.setup()

from sparkzoneapp.models import User, ProviderProfile, Country, State, City, Category, Game, Slot, GameImages

def seed():
    print("Seeding initial location, category, game, provider, and slot data...")
    
    # 1. Country & States & Cities
    india, _ = Country.objects.get_or_create(name="India")
    
    gj, _ = State.objects.get_or_create(country=india, name="Gujarat")
    mh, _ = State.objects.get_or_create(country=india, name="Maharashtra")
    ka, _ = State.objects.get_or_create(country=india, name="Karnataka")

    ahmedabad, _ = City.objects.get_or_create(state=gj, name="Ahmedabad")
    mumbai, _ = City.objects.get_or_create(state=mh, name="Mumbai")
    bengaluru, _ = City.objects.get_or_create(state=ka, name="Bengaluru")

    # 2. Demo Provider Account
    provider_user, u_created = User.objects.get_or_create(
        email="provider@sparkzone.in",
        defaults={
            "firstName": "Apex",
            "lastName": "Gaming",
            "password": hashlib.sha256("Provider@1234".encode()).hexdigest(),
            "role": "provider"
        }
    )

    provider_profile, p_created = ProviderProfile.objects.get_or_create(
        user=provider_user,
        defaults={
            "businessName": "CyberX Arena Lounge",
            "phone": 9313858614,
            "address": "CG Road, Navrangpura, Ahmedabad",
            "city": ahmedabad,
            "is_verified": True
        }
    )

    # 3. Categories with cover photo URLs
    categories_data = [
        {
            "categoryName": "Action & Adventure",
            "description": "High-octane action, open-world exploration, and immersive storylines.",
            "image": "Category/openworld.jfif",
            "image_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=600&q=80"
        },
        {
            "categoryName": "FPS & Shooter",
            "description": "Fast-paced tactical first-person shooters and multiplayer battle arenas.",
            "image_url": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?auto=format&fit=crop&w=600&q=80"
        },
        {
            "categoryName": "Racing & Sports",
            "description": "Supercars, realistic physics, and adrenaline-pumping racing games.",
            "image_url": "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=600&q=80"
        }
    ]

    category_objs = {}
    for cdata in categories_data:
        cat, created = Category.objects.get_or_create(
            categoryName=cdata["categoryName"],
            defaults=cdata
        )
        if not cat.image and cdata.get("image"):
            cat.image = cdata["image"]
            cat.save()
        if not cat.image_url:
            cat.image_url = cdata["image_url"]
            cat.save()
        category_objs[cdata["categoryName"]] = cat

    # 4. Games with Provider link & High-res cover photos
    games_data = [
        {
            "name": "Grand Theft Auto VI",
            "provider": provider_profile,
            "category": category_objs["Action & Adventure"],
            "city": ahmedabad,
            "description": "Experience the ultimate next-gen open world gaming station with Vice City & RTX 4090 performance.",
            "address": "SparkZone Arena, CG Road, Ahmedabad",
            "pricePerHour": 250.0,
            "totalSystem": 10,
            "availableSystems": 8,
            "image": "Game/GTA6IMAGE.jfif",
            "image_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=80",
            "status": "active"
        },
        {
            "name": "Cyberpunk 2077: Phantom Liberty",
            "provider": provider_profile,
            "category": category_objs["Action & Adventure"],
            "city": mumbai,
            "description": "Dive into Night City with full Ray Tracing, 4K OLED display, and haptic feedback gear.",
            "address": "SparkZone Hub, Bandra West, Mumbai",
            "pricePerHour": 300.0,
            "totalSystem": 8,
            "availableSystems": 6,
            "image_url": "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=800&q=80",
            "status": "active"
        },
        {
            "name": "Valorant Pro Arena",
            "provider": provider_profile,
            "category": category_objs["FPS & Shooter"],
            "city": bengaluru,
            "description": "360Hz Esports monitors, low-latency mechanical keyboards, and 1Gbps fiber gaming line.",
            "address": "SparkZone Lounge, Indiranagar, Bengaluru",
            "pricePerHour": 180.0,
            "totalSystem": 15,
            "availableSystems": 12,
            "image_url": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?auto=format&fit=crop&w=800&q=80",
            "status": "active"
        },
        {
            "name": "Forza Horizon 5 Simulator",
            "provider": provider_profile,
            "category": category_objs["Racing & Sports"],
            "city": ahmedabad,
            "description": "Full motion simulator rig with Fanatec direct drive wheel, pedals, and VR headset.",
            "address": "SparkZone Arena, SG Highway, Ahmedabad",
            "pricePerHour": 350.0,
            "totalSystem": 4,
            "availableSystems": 3,
            "image_url": "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=800&q=80",
            "status": "active"
        },
        {
            "name": "Call of Duty: Warzone",
            "provider": provider_profile,
            "category": category_objs["FPS & Shooter"],
            "city": mumbai,
            "description": "Battle royale squad stations equipped with surround sound headsets and 240Hz monitors.",
            "address": "SparkZone Hub, Andheri East, Mumbai",
            "pricePerHour": 220.0,
            "totalSystem": 12,
            "availableSystems": 10,
            "image_url": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=800&q=80",
            "status": "active"
        }
    ]

    from datetime import date, time
    today = date.today()

    for gdata in games_data:
        game, created = Game.objects.get_or_create(
            name=gdata["name"],
            defaults=gdata
        )
        if not game.provider:
            game.provider = provider_profile
            game.save()
        if not game.image and gdata.get("image"):
            game.image = gdata["image"]
            game.save()
        if not game.image_url:
            game.image_url = gdata["image_url"]
            game.save()

        # Add gallery images for GTA VI if present
        if game.name == "Grand Theft Auto VI":
            gallery_photos = ["Games/Brian.webp", "Games/Jason.webp", "Games/Raul.webp"]
            for photo in gallery_photos:
                GameImages.objects.get_or_create(game=game, image=photo)

        # Seed sample provider slots for game
        Slot.objects.get_or_create(
            game=game,
            slotDate=today,
            startTime=time(14, 0),
            endTime=time(16, 0),
            defaults={"capacity": game.totalSystem, "price": game.pricePerHour, "status": "available"}
        )
        Slot.objects.get_or_create(
            game=game,
            slotDate=today,
            startTime=time(18, 0),
            endTime=time(20, 0),
            defaults={"capacity": game.totalSystem, "price": game.pricePerHour, "status": "available"}
        )

    print("Seeding completed successfully with provider and slots!")

if __name__ == "__main__":
    seed()
