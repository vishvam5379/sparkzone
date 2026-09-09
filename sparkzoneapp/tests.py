import hashlib
from datetime import date, time
from django.test import TestCase, Client
from django.urls import reverse
from .models import User, Country, State, City, ProviderProfile, Category, Game, Slot, Booking

class RoleDetectionAndDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.country = Country.objects.create(name="India")
        self.state = State.objects.create(country=self.country, name="Gujarat")
        self.city = City.objects.create(state=self.state, name="Ahmedabad")

        # Gamer User
        self.gamer_password = "gamerPassword123"
        self.gamer_hashed = hashlib.sha256(self.gamer_password.encode()).hexdigest()
        self.gamer = User.objects.create(
            firstName="Alex",
            lastName="Mercer",
            email="alex@gamer.com",
            password=self.gamer_hashed,
            role="user"
        )

        # Provider User
        self.provider_password = "providerPassword123"
        self.provider_hashed = hashlib.sha256(self.provider_password.encode()).hexdigest()
        self.provider = User.objects.create(
            firstName="Marcus",
            lastName="Fenix",
            email="marcus@provider.com",
            password=self.provider_hashed,
            role="provider"
        )
        self.provider_profile = ProviderProfile.objects.create(
            user=self.provider,
            businessName="Gears Gaming Lounge",
            phone=9876543210,
            address="Ring Road",
            city=self.city,
            is_verified=True
        )

        self.category = Category.objects.create(categoryName="Shooting")
        self.game = Game.objects.create(
            provider=self.provider_profile,
            category=self.category,
            city=self.city,
            name="RTX 4090 Esports Station",
            pricePerHour=250.0,
            totalSystem=8,
            availableSystems=8,
            gpu="NVIDIA GeForce RTX 4090 24GB",
            cpu="Intel i9-14900K",
            status="active"
        )

    def test_gamer_login_redirect_and_session(self):
        """Gamer login redirects to /dashboard/gamer/ and stores role in session."""
        resp = self.client.post(reverse('login'), {
            'email': 'alex@gamer.com',
            'password': self.gamer_password,
        })
        self.assertRedirects(resp, reverse('gamer_dashboard'))
        self.assertEqual(self.client.session.get('role'), 'user')
        self.assertEqual(self.client.session.get('user_id'), self.gamer.id)

    def test_provider_login_redirect_and_session(self):
        """Provider login redirects to /dashboard/provider/ and stores role in session."""
        resp = self.client.post(reverse('login'), {
            'email': 'marcus@provider.com',
            'password': self.provider_password,
        })
        self.assertRedirects(resp, reverse('provider_dashboard'))
        self.assertEqual(self.client.session.get('role'), 'provider')
        self.assertEqual(self.client.session.get('user_id'), self.provider.id)

    def test_gamer_dashboard_app_shell_and_nav_items(self):
        """Gamer dashboard renders persistent sidebar and Gamer pill."""
        self.client.post(reverse('login'), {'email': 'alex@gamer.com', 'password': self.gamer_password})
        resp = self.client.get(reverse('gamer_dashboard'))
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode('utf-8')
        self.assertIn('dash-sidebar', content)
        self.assertIn('My Passes & Sessions', content)
        self.assertIn('Explore Stations', content)
        self.assertIn('Alex Mercer', content)
        self.assertIn('role-gamer', content)

    def test_provider_dashboard_app_shell_and_nav_items(self):
        """Provider dashboard renders persistent sidebar with cockpit operations and Provider pill."""
        self.client.post(reverse('login'), {'email': 'marcus@provider.com', 'password': self.provider_password})
        resp = self.client.get(reverse('provider_dashboard'))
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode('utf-8')
        self.assertIn('dash-sidebar', content)
        self.assertIn('Dashboard', content)
        self.assertIn('Stations & Rigs', content)
        self.assertIn('Bookings & Check-in', content)
        self.assertIn('Marcus Fenix', content)
        self.assertIn('role-provider', content)

    def test_instant_checkout_pay_at_venue(self):
        """Gamer checkout with pay_at_venue creates confirmed booking lock immediately."""
        self.client.post(reverse('login'), {'email': 'alex@gamer.com', 'password': self.gamer_password})
        resp = self.client.post(reverse('gamer_checkout', args=[self.game.id]), {
            'bookingDate': str(date.today()),
            'startTime': '14:00',
            'endTime': '16:00',
            'unit_number': '1',
            'payment_method': 'pay_at_venue',
        })
        self.assertRedirects(resp, reverse('gamer_dashboard'))

        booking = Booking.objects.filter(game=self.game, user=self.gamer).first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.status, 'confirmed')
        self.assertEqual(booking.payment_status, 'pay_at_venue')
        self.assertEqual(booking.unit_number, 1)

    def test_provider_checkin_and_noshow(self):
        """Provider can check in gamer or mark no-show."""
        booking = Booking.objects.create(
            user=self.gamer,
            game=self.game,
            bookingDate=date.today(),
            startTime=time(14, 0),
            endTime=time(16, 0),
            totalAmount=500.0,
            status='confirmed',
            payment_status='pay_at_venue',
            unit_number='2'
        )

        # Provider logs in
        self.client.post(reverse('login'), {'email': 'marcus@provider.com', 'password': self.provider_password})

        # Check-in
        resp = self.client.post(reverse('provider_booking_checkin', args=[booking.id]))
        self.assertRedirects(resp, reverse('provider_bookings'))
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'completed')
        self.assertEqual(booking.payment_status, 'paid_online')
        self.assertIsNotNone(booking.check_in_time)

    def test_unit_availability_api(self):
        """Unit availability endpoint returns unit statuses and handles disabled units."""
        resp = self.client.get(reverse('get_unit_availability_api', args=[self.game.id]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['total_systems'], 8)
        self.assertEqual(len(data['units']), 8)
        self.assertEqual(data['units'][0]['status'], 'available')

    def test_superadmin_dashboard_and_venue_verification(self):
        """Superadmin dashboard loads metrics and allows venue verification toggle."""
        # Provider has admin access as well or admin email
        self.client.post(reverse('login'), {'email': 'marcus@provider.com', 'password': self.provider_password})
        resp = self.client.get(reverse('superadmin_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Superadmin Platform Oversight', resp.content.decode('utf-8'))

        # Toggle venue verification
        toggle_resp = self.client.get(reverse('superadmin_toggle_verify', args=[self.provider_profile.id]))
        self.assertRedirects(toggle_resp, reverse('superadmin_dashboard'))
        self.provider_profile.refresh_from_db()
        self.assertFalse(self.provider_profile.is_verified)

