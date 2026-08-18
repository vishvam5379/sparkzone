import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if available
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-l@j!&aml_t*9^uvfu4#v-)cr4pn!+=-!7arp4)wf14#^y(^=s5')

DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '*').split(',') if h.strip()]
vercel_url = os.getenv('VERCEL_URL')
if vercel_url:
    clean_vurl = vercel_url.replace('https://', '').replace('http://', '').strip('/')
    ALLOWED_HOSTS.append(clean_vurl)

# Reverse Proxy / Vercel / Railway HTTPS Detection
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# CSRF Trusted Origins for Vercel & Railway HTTPS domains
csrf_origins_env = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'https://*.vercel.app,https://web-production-71ccf.up.railway.app,https://*.up.railway.app,https://*.railway.app,https://*.onrender.com,http://localhost,http://127.0.0.1'
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_origins_env.split(',') if o.strip()]

if vercel_url:
    clean_domain = vercel_url.replace('https://', '').replace('http://', '').strip('/')
    CSRF_TRUSTED_ORIGINS.extend([f"https://{clean_domain}", f"http://{clean_domain}"])

railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN') or os.getenv('RAILWAY_STATIC_URL')
if railway_domain:
    clean_domain = railway_domain.replace('https://', '').replace('http://', '').strip('/')
    CSRF_TRUSTED_ORIGINS.extend([f"https://{clean_domain}", f"http://{clean_domain}"])

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "sparkzoneapp"
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sparkzoneproject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sparkzoneproject.wsgi.application'

# Session & Cookie Security Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', 1209600))  # 2 weeks (1,209,600 seconds)
SESSION_SAVE_EVERY_REQUEST = True  # Enable sliding expiration (refreshes session age on every request)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_AGE = 31449600  # 1 year

# Secure cookies and headers in production (HTTPS)
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'


# Database Configuration
# Uses DATABASE_URL environment variable if set (Railway / Neon / Supabase Postgres)
# Falls back to SQLite for local development or Vercel serverless environment
IS_VERCEL = os.getenv('VERCEL') == '1' or 'VERCEL' in os.environ or os.path.exists('/var/task')

raw_db_url = os.getenv('DATABASE_URL')
if raw_db_url:
    import re
    match = re.search(r'postgres(?:ql)?://[^\s\'"]+', raw_db_url)
    if match:
        clean_url = match.group(0)
        if 'sslmode=require' in clean_url:
            clean_url = clean_url.split('sslmode=require')[0] + 'sslmode=require'
        raw_db_url = clean_url
        os.environ['DATABASE_URL'] = clean_url

if IS_VERCEL and not raw_db_url:
    db_path = Path('/tmp/db.sqlite3')
    source_db = BASE_DIR / 'db.sqlite3'
    if source_db.exists() and not db_path.exists():
        try:
            import shutil
            shutil.copy2(source_db, db_path)
        except Exception:
            pass
    default_db_url = f"sqlite:///{db_path}"
else:
    default_db_url = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"

DATABASES = {
    'default': dj_database_url.parse(
        raw_db_url or default_db_url,
        conn_max_age=int(os.getenv('CONN_MAX_AGE', 600)),
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"
