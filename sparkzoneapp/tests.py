import hashlib
from django.test import TestCase, Client
from django.urls import reverse
from .models import User, Country, State, City, ProviderProfile

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

    def test_gamer_login_redirect_and_session(self):
        """Gamer login without role selector redirects to /dashboard/gamer/ and stores role in session."""
        resp = self.client.post(reverse('login'), {
            'email': 'alex@gamer.com',
            'password': self.gamer_password,
        })
        self.assertRedirects(resp, reverse('gamer_dashboard'))
        self.assertEqual(self.client.session.get('role'), 'user')
        self.assertEqual(self.client.session.get('user_id'), self.gamer.id)

    def test_provider_login_redirect_and_session(self):
        """Provider login without role selector redirects to /dashboard/provider/ and stores role in session."""
        resp = self.client.post(reverse('login'), {
            'email': 'marcus@provider.com',
            'password': self.provider_password,
        })
        self.assertRedirects(resp, reverse('provider_dashboard'))
        self.assertEqual(self.client.session.get('role'), 'provider')
        self.assertEqual(self.client.session.get('user_id'), self.provider.id)

    def test_gamer_dashboard_app_shell_and_nav_items(self):
        """Gamer dashboard renders persistent sidebar with Bookings, Find Stations, Wallet, Settings and Gamer pill."""
        # Login first
        self.client.post(reverse('login'), {'email': 'alex@gamer.com', 'password': self.gamer_password})
        resp = self.client.get(reverse('gamer_dashboard'))
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode('utf-8')
        # Check distinct shell sidebar exists
        self.assertIn('dash-sidebar', content)
        # Check role-specific nav items for Gamer
        self.assertIn('Bookings', content)
        self.assertIn('Find Stations', content)
        self.assertIn('Wallet', content)
        self.assertIn('Settings', content)
        # Check top bar user name and role badge pill
        self.assertIn('Alex Mercer', content)
        self.assertIn('Gamer', content)
        self.assertIn('role-gamer', content)

    def test_provider_dashboard_app_shell_and_nav_items(self):
        """Provider dashboard renders persistent sidebar with My Listings, Bookings, Earnings, Settings and Provider pill."""
        # Login first
        self.client.post(reverse('login'), {'email': 'marcus@provider.com', 'password': self.provider_password})
        resp = self.client.get(reverse('provider_dashboard'))
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode('utf-8')
        # Check distinct shell sidebar exists
        self.assertIn('dash-sidebar', content)
        # Check role-specific nav items for Provider
        self.assertIn('My Listings', content)
        self.assertIn('Bookings', content)
        self.assertIn('Earnings', content)
        self.assertIn('Settings', content)
        # Check top bar user name and role badge pill
        self.assertIn('Marcus Fenix', content)
        self.assertIn('Provider', content)
        self.assertIn('role-provider', content)

    def test_complete_profile_for_pending_user(self):
        """Brand-new user with pending role is directed to complete profile and can choose Gamer or Provider."""
        pending_user = User.objects.create(
            firstName="Sam",
            lastName="Fisher",
            email="sam@splinter.com",
            password="pwd",
            role="pending"
        )
        session = self.client.session
        session['user_id'] = pending_user.id
        session['role'] = 'pending'
        session.save()

        # Accessing complete-profile screen
        resp = self.client.get(reverse('complete_profile'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('I am a Gamer', resp.content.decode('utf-8'))
        self.assertIn('I am a Provider', resp.content.decode('utf-8'))

        # Submitting choice as Gamer
        resp_post = self.client.post(reverse('complete_profile'), {'role': 'user'})
        self.assertRedirects(resp_post, reverse('gamer_dashboard'))
        pending_user.refresh_from_db()
        self.assertEqual(pending_user.role, 'user')
        self.assertEqual(self.client.session.get('role'), 'user')
