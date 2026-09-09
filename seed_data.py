import os
import django
import hashlib
from datetime import date, time, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sparkzoneproject.settings')
django.setup()

from sparkzoneapp.models import (
    User, ProviderProfile, Country, State, City, Category,
    Game, Slot, GameImages, Reviews, FavoriteVenue
)

def seed():
    print("Seeding production-grade multi-venue data with real hardware specs, slots, and verified reviews...")

    # 1. Locations
    india, _ = Country.objects.get_or_create(name="India")
    gj, _ = State.objects.get_or_create(country=india, name="Gujarat")
    mh, _ = State.objects.get_or_create(country=india, name="Maharashtra")
    ka, _ = State.objects.get_or_create(country=india, name="Karnataka")

    ahmedabad, _ = City.objects.get_or_create(state=gj, name="Ahmedabad")
    mumbai, _ = City.objects.get_or_create(state=mh, name="Mumbai")
    bengaluru, _ = City.objects.get_or_create(state=ka, name="Bengaluru")

    # 2. Providers / Lounges
    providers_data = [
        {
            "email": "provider@sparkzone.in",
            "firstName": "Apex",
            "lastName": "Gaming",
            "businessName": "CyberX Arena & Esports Lounge",
            "phone": 9313858614,
            "address": "402 Sapphire Complex, CG Road, Navrangpura",
            "city": ahmedabad
        },
        {
            "email": "velocity.sims@sparkzone.in",
            "firstName": "Marcus",
            "lastName": "Vance",
            "businessName": "Velocity Motion Sim Lab",
            "phone": 9820145890,
            "address": "Plot 18, Hill Road, Bandra West",
            "city": mumbai
        },
        {
            "email": "pixelforge@sparkzone.in",
            "firstName": "Rohan",
            "lastName": "Sen",
            "businessName": "PixelForge Cyber Cafe",
            "phone": 9988776655,
            "address": "100 Feet Road, HAL 2nd Stage, Indiranagar",
            "city": bengaluru
        }
    ]

    provider_profiles = {}
    for pdata in providers_data:
        p_user, _ = User.objects.get_or_create(
            email=pdata["email"],
            defaults={
                "firstName": pdata["firstName"],
                "lastName": pdata["lastName"],
                "password": hashlib.sha256("Provider@1234".encode()).hexdigest(),
                "role": "provider"
            }
        )
        p_profile, _ = ProviderProfile.objects.get_or_create(
            user=p_user,
            defaults={
                "businessName": pdata["businessName"],
                "phone": pdata["phone"],
                "address": pdata["address"],
                "city": pdata["city"],
                "is_verified": True
            }
        )
        provider_profiles[pdata["businessName"]] = p_profile

    # 3. Categories
    categories_data = [
        {"categoryName": "Shooting", "description": "Esports tactical FPS stations, 360Hz monitors, low-latency mechanical keyboards.", "image_url": "/static/images/categories/shooting.webp"},
        {"categoryName": "Racing", "description": "Full-motion direct-drive racing simulators with load-cell pedals and triple curved displays.", "image_url": "/static/images/categories/racing.webp"},
        {"categoryName": "Open World", "description": "Ultra-high graphics 4K OLED stations for open world immersion and AAA story titles.", "image_url": "/static/images/categories/open_world.webp"},
        {"categoryName": "Fighting", "description": "Arcade fight sticks, low input lag 240Hz monitors, and head-to-head fighting setups.", "image_url": "/static/images/categories/fighting.webp"},
        {"categoryName": "Sports", "description": "Next-gen sports gaming stations featuring FIFA, NBA, and championship cricket.", "image_url": "/static/images/categories/sports.webp"},
        {"categoryName": "RPG", "description": "Cinematic role-playing rigs with surround sound and high-fidelity ray tracing.", "image_url": "/static/images/categories/rpg.webp"},
    ]

    cat_objs = {}
    for cdata in categories_data:
        cat, _ = Category.objects.get_or_create(
            categoryName=cdata["categoryName"],
            defaults=cdata
        )
        cat_objs[cdata["categoryName"]] = cat

    # 4. Realistic Gaming Stations with Full Hardware Specs
    cyberx_provider = provider_profiles["CyberX Arena & Esports Lounge"]
    velocity_provider = provider_profiles["Velocity Motion Sim Lab"]
    pixelforge_provider = provider_profiles["PixelForge Cyber Cafe"]

    stations_data = [
        {
            "name": "RTX 4090 Tournament Battle-Station",
            "provider": cyberx_provider,
            "category": cat_objs["Shooting"],
            "city": ahmedabad,
            "description": "Premier esports competition station tuned for zero latency. Liquid-cooled RTX 4090 rig running competitive titles with steady 360+ FPS.",
            "address": "CyberX Arena, 4th Floor, Sapphire Complex, CG Road, Ahmedabad",
            "pricePerHour": 280.0,
            "totalSystem": 8,
            "availableSystems": 8,
            "gpu": "NVIDIA GeForce RTX 4090 24GB",
            "cpu": "Intel Core i9-14900K 24-Core 6.0GHz",
            "ram": "32GB DDR5 6000MHz Corsair Dominator",
            "display_specs": "27\" ROG Swift 360Hz Fast-IPS 1440p (0.03ms)",
            "peripherals": "Wooting 60HE Hall-Effect Keyboard, Logitech G Pro X Superlight 2, Sennheiser HD660S Headset",
            "available_games": "Valorant, Counter-Strike 2, Apex Legends, Call of Duty: Warzone, Rainbow Six Siege",
            "operating_hours": "09:00 AM - 11:30 PM",
            "featured": True,
            "image_url": "/static/images/stations/esports_station.jpg"
        },
        {
            "name": "PlayStation 5 VIP Recliner Lounge",
            "provider": cyberx_provider,
            "category": cat_objs["Open World"],
            "city": ahmedabad,
            "description": "Private VIP console booth with leather recliners and 65-inch LG OLED display for top-tier console action and cooperative gaming.",
            "address": "CyberX Arena, 4th Floor, Sapphire Complex, CG Road, Ahmedabad",
            "pricePerHour": 240.0,
            "totalSystem": 6,
            "availableSystems": 6,
            "gpu": "Custom AMD RDNA 2 GPU (10.3 TFLOPS)",
            "cpu": "Custom 8-Core AMD Zen 2 CPU",
            "ram": "16GB GDDR6 Unified High-Speed Memory",
            "display_specs": "65\" LG C3 4K 120Hz G-Sync OLED TV",
            "peripherals": "DualSense Edge Wireless Controller with paddle shifters, SteelSeries Arctis Nova Pro Wireless",
            "available_games": "Grand Theft Auto VI, Spider-Man 2, God of War Ragnarök, EA Sports FC 24, Tekken 8",
            "operating_hours": "10:00 AM - 11:00 PM",
            "featured": True,
            "image_url": "/static/images/stations/ps5_lounge.jpg"
        },
        {
            "name": "Fanatec Direct-Drive Pro Motion Cockpit",
            "provider": velocity_provider,
            "category": cat_objs["Racing"],
            "city": mumbai,
            "description": "Industrial grade motion sim platform with 25Nm direct-drive steering torque, load-cell hydraulic braking, and triple panoramic wraparound screens.",
            "address": "Velocity Motion Sim Lab, Plot 18, Hill Road, Bandra West, Mumbai",
            "pricePerHour": 450.0,
            "totalSystem": 4,
            "availableSystems": 4,
            "gpu": "NVIDIA GeForce RTX 4090 24GB Liquid-Cooled",
            "cpu": "AMD Ryzen 7 7800X3D 3D V-Cache",
            "ram": "64GB DDR5 6000MHz Low-Latency",
            "display_specs": "Triple 32\" Samsung Odyssey G7 240Hz 1000R Curved Displays",
            "peripherals": "Fanatec Podium DD2 25Nm Wheelbase, ClubSport V3 Load-Cell Pedals, NextLevel Racing Motion Platform Plus",
            "available_games": "Assetto Corsa Competizione, F1 24, iRacing, Forza Horizon 5, Dirt Rally 2.0",
            "operating_hours": "11:00 AM - 11:00 PM",
            "featured": True,
            "image_url": "/static/images/stations/sim_racing_rig.jpg"
        },
        {
            "name": "RTX 4080 Super Esports Rig",
            "provider": pixelforge_provider,
            "category": cat_objs["Shooting"],
            "city": bengaluru,
            "description": "High performance multiplayer battle station crafted for competitive scrims, ranked matches, and LAN tournaments.",
            "address": "PixelForge Cyber Cafe, 100 Feet Road, Indiranagar, Bengaluru",
            "pricePerHour": 220.0,
            "totalSystem": 12,
            "availableSystems": 12,
            "gpu": "NVIDIA GeForce RTX 4080 Super 16GB",
            "cpu": "AMD Ryzen 7 7800X3D 8-Core",
            "ram": "32GB DDR5 5600MHz Kingston Fury",
            "display_specs": "27\" BenQ ZOWIE XL2566K 360Hz DyAc+ Esports Monitor",
            "peripherals": "Razer Huntsman V3 Pro, Razer DeathAdder V3 Pro, HyperX Cloud III Wireless",
            "available_games": "Valorant, Counter-Strike 2, Overwatch 2, Apex Legends, PUBG",
            "operating_hours": "09:00 AM - 11:00 PM",
            "featured": False,
            "image_url": "/static/images/stations/pro_arena_rig.jpg"
        },
        {
            "name": "Arcade & Fighting Pro Booth",
            "provider": pixelforge_provider,
            "category": cat_objs["Fighting"],
            "city": bengaluru,
            "description": "Lag-free 1v1 fighting setup equipped with Qanba Obsidian tournament fightsticks and competitive settings.",
            "address": "PixelForge Cyber Cafe, 100 Feet Road, Indiranagar, Bengaluru",
            "pricePerHour": 190.0,
            "totalSystem": 6,
            "availableSystems": 6,
            "gpu": "NVIDIA GeForce RTX 4070 Ti Super 16GB",
            "cpu": "Intel Core i7-14700K 20-Core",
            "ram": "32GB DDR5 5600MHz",
            "display_specs": "25\" ASUS TUF 280Hz 0.5ms Fast-IPS",
            "peripherals": "Qanba Obsidian 2 Arcade Fightstick, Dual Hori Fighting Commanders, Audio-Technica ATH-M50x",
            "available_games": "Street Fighter 6, Tekken 8, Mortal Kombat 1, Guilty Gear Strive, Dragon Ball FighterZ",
            "operating_hours": "10:00 AM - 10:30 PM",
            "featured": False,
            "image_url": "/static/images/stations/esports_station.jpg"
        }
    ]

    today = date.today()
    all_game_objs = []
    slots_to_create = []

    for sdata in stations_data:
        game, created = Game.objects.get_or_create(
            name=sdata["name"],
            defaults=sdata
        )
        # Update fields if already exists
        for key, val in sdata.items():
            setattr(game, key, val)
        game.status = 'active'
        game.save()
        all_game_objs.append(game)

        # Generate realistic slots for today and next 5 days
        for day_offset in range(6):
            slot_date = today + timedelta(days=day_offset)
            hours_schedule = [
                (10, 12),
                (12, 14),
                (14, 16),
                (16, 18),
                (18, 20),
                (20, 22),
            ]
            for start_h, end_h in hours_schedule:
                slots_to_create.append(Slot(
                    game=game,
                    slotDate=slot_date,
                    startTime=time(start_h, 0),
                    endTime=time(end_h, 0),
                    capacity=game.totalSystem,
                    bookedCount=0,
                    price=game.pricePerHour,
                    status="available"
                ))

    # Bulk create slots in single query
    Slot.objects.bulk_create(slots_to_create, ignore_conflicts=True)

    # 5. Seed Real Verified Reviews
    gamer_user, _ = User.objects.get_or_create(
        email="sukhadiyavishvam22@gmail.com",
        defaults={
            "firstName": "Vishvam",
            "lastName": "Sukhadiya",
            "password": hashlib.sha256("Gamer@1234".encode()).hexdigest(),
            "role": "user"
        }
    )

    alex_gamer, _ = User.objects.get_or_create(
        email="gamer@sparkzone.in",
        defaults={
            "firstName": "Alex",
            "lastName": "Gamer",
            "password": hashlib.sha256("Gamer@1234".encode()).hexdigest(),
            "role": "user"
        }
    )

    sample_reviews = [
        {
            "user": gamer_user,
            "game": all_game_objs[0],
            "rating": 5.0,
            "comment": "The 360Hz monitor and Wooting keyboard give insane competitive edge in Valorant. Zero input lag, rock-solid 400+ FPS."
        },
        {
            "user": alex_gamer,
            "game": all_game_objs[1],
            "rating": 5.0,
            "comment": "Best PS5 lounge in Ahmedabad! The 65-inch LG OLED and leather recliners are top notch for FIFA and Spider-Man with friends."
        },
        {
            "user": gamer_user,
            "game": all_game_objs[2],
            "rating": 5.0,
            "comment": "The Fanatec direct-drive force feedback and triple curved screens in Bandra are incredible. Felt like driving an actual GT3 car."
        },
        {
            "user": alex_gamer,
            "game": all_game_objs[3],
            "rating": 4.8,
            "comment": "Ultra fast internet, clean acoustics, and crisp DyAc+ monitors in Indiranagar. Great for team scrims."
        }
    ]

    for rev in sample_reviews:
        Reviews.objects.update_or_create(
            user=rev["user"],
            game=rev["game"],
            defaults={
                "rating": rev["rating"],
                "comment": rev["comment"],
                "is_verified_booking": True
            }
        )

    # 6. Favorite bookmark
    FavoriteVenue.objects.get_or_create(user=gamer_user, game=all_game_objs[0])
    FavoriteVenue.objects.get_or_create(user=gamer_user, game=all_game_objs[2])

    print("[SUCCESS] Successfully seeded real venues, hardware specs, slots, and verified gamer reviews!")

if __name__ == "__main__":
    seed()
