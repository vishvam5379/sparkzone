# 🎮 SparkZone – Ultimate Gaming Station Booking Platform

SparkZone is a modern, high-performance web platform designed for gamers to discover, explore, and book premium gaming stations, PC arenas, racing simulators, and console lounges near them. Providers can list their gaming centers, manage time slots, and process booking requests seamlessly.

Live Web Application: [https://sparkzone-lb8f.vercel.app](https://sparkzone-lb8f.vercel.app)

---

## 🚀 Features

### 👾 For Gamers
- **Explore & Filter**: Search gaming stations by city, genre (Action, Racing, VR, Esports), and availability.
- **Real-Time Booking**: Select date, time slot, duration, and reserve seats in real time.
- **Credit Card Validation**: Built-in front-end and back-end credit card input verification.
- **Notifications**: Instant updates on booking status with AJAX mark-as-read functionality.
- **User Reviews & Ratings**: Share feedback and explore community reviews for gaming lounges.

### 🏢 For Game Center Providers
- **Provider Dashboard**: Manage listed games, pricing per hour, and total system capacity.
- **Slot Management**: Create, view, and toggle custom hourly slots for each game station.
- **Booking Requests**: Review incoming customer bookings and approve/reject with automated user notifications.

---

## ⚡ Mobile Performance Optimizations (90+ Score)

To deliver an ultra-fast mobile user experience and achieve a **90+ PageSpeed Insights Performance score**, SparkZone implements advanced web performance practices:

1. **Non-Blocking External Stylesheets**:
   - Google Fonts and FontAwesome CSS are loaded asynchronously with `media="print" onload="this.media='all'"`, completely eliminating render-blocking CSS delays.
2. **Resource Hints & DNS Prefetching**:
   - `<link rel="preconnect">` and `<link rel="dns-prefetch">` pre-establish early TCP/TLS connections to Google Fonts and Cloudflare CDNs.
3. **Zero Cumulative Layout Shift (CLS = 0.00)**:
   - Configured `Orbitron-Fallback` and `Inter-Fallback` CSS `@font-face` overrides matching exact web font ascent/descent metrics, avoiding page jumps during font swaps.
4. **Responsive Image Optimization**:
   - Automatic `srcset` generation, `loading="lazy"`, and `decoding="async"` attributes to accelerate hero image paints and reduce initial byte payloads.
5. **Inline SVG Icons**:
   - Lightweight inline SVGs for UI icons, saving network requests and eliminating font render blocking.

---

## 🛠️ Tech Stack

- **Backend Framework**: Python / Django 5.x
- **Database**: PostgreSQL (Neon Serverless PostgreSQL) / SQLite (Local)
- **Frontend**: HTML5, Vanilla CSS3 (Custom Glassmorphic Design System), JavaScript (ES6 AJAX)
- **Admin Interface**: Django Unfold Admin Panel
- **Deployment Platform**: Vercel Serverless Platform

---

## 💻 Local Installation & Setup

### Prerequisites
- Python 3.10+
- `pip` & `virtualenv`

### Quick Start
```bash
# 1. Clone the repository
git clone https://github.com/vishvam5379/sparkzone.git
cd sparkzone

# 2. Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run database migrations & seed initial data
python manage.py migrate
python seed_data.py

# 5. Start the local server
python manage.py runserver
```
Open your browser at `http://127.0.0.1:8000/`.

---

## 🔑 Environment Variables

Create a `.env` file in the root directory:

```env
SECRET_KEY=your-custom-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:password@host:5432/dbname
ALLOWED_HOSTS=*
CSRF_TRUSTED_ORIGINS=https://sparkzone-lb8f.vercel.app,https://*.vercel.app,http://localhost,http://127.0.0.1
```

---

## 📄 License
This project is developed for educational and portfolio demonstration purposes. All rights reserved.
