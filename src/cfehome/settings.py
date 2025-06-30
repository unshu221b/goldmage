

from pathlib import Path
import os
from decouple import config, Csv
import logging
from datetime import timedelta

if os.environ.get("GOOGLE_CREDENTIALS_JSON"):
    creds_path = "/tmp/gcloud-credentials.json"
    with open(creds_path, "w") as f:
        f.write(os.environ["GOOGLE_CREDENTIALS_JSON"])
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

BASE_URL = config("BASE_URL", default='http://127.0.0.1:8000')
# default backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config("EMAIL_HOST", cast=str, default=None)
EMAIL_PORT = config("EMAIL_PORT", cast=str, default='587') # Recommended
EMAIL_ADDRESS = "charleslung221b@gmail.com"
EMAIL_HOST_USER = config("EMAIL_HOST_USER", cast=str, default=None)
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", cast=str, default=None)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool, default=True)  # Use EMAIL_PORT 587 for TLS

ADMIN_USER_NAME=config("ADMIN_USER_NAME", default="Charles")
ADMIN_USER_EMAIL=config("ADMIN_USER_EMAIL", default=None)

# Custom user model
AUTH_USER_MODEL = "accounts.CustomUser"

MANAGERS=[]
ADMINS=[]
if all([ADMIN_USER_NAME, ADMIN_USER_EMAIL]):
    ADMINS +=[
        (f'{ADMIN_USER_NAME}', f'{ADMIN_USER_EMAIL}')
    ]
    MANAGERS=ADMINS

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_CDN = BASE_DIR.parent / "local-cdn"
TEMPLATE_DIR = BASE_DIR / "templates"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

# Base allowed hosts (always include these)
BASE_ALLOWED_HOSTS = [
    "0.0.0.0",
    "localhost",
    "127.0.0.1",
]

# Get additional hosts from environment
ENV_ALLOWED_HOSTS = config("ALLOWED_HOSTS", 
                         default="52aichan.com,.52aichan.com", 
                         cast=Csv())
ALLOWED_HOSTS = BASE_ALLOWED_HOSTS + list(ENV_ALLOWED_HOSTS)

OPENAI_API_KEY = config("OPENAI_API_KEY")
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = config("STRIPE_PUBLIC_KEY")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET")
STRIPE_MONTHLY_PRICE_ID = config("STRIPE_MONTHLY_PRICE_ID")
STRIPE_YEARLY_PRICE_ID = config("STRIPE_YEARLY_PRICE_ID")
# Credit Product Price IDs
STRIPE_CREDIT_SMALL_PRICE_ID = config("STRIPE_CREDIT_SMALL_PRICE_ID", default="")
STRIPE_CREDIT_MEDIUM_PRICE_ID = config("STRIPE_CREDIT_MEDIUM_PRICE_ID", default="")
STRIPE_CREDIT_LARGE_PRICE_ID = config("STRIPE_CREDIT_LARGE_PRICE_ID", default="")


# Clerk Config
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = config("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
CLERK_SECRET_KEY = config("CLERK_SECRET_KEY")
CLERK_WEBHOOK_SIGNING_SECRET = config("CLERK_WEBHOOK_SIGNING_SECRET")
CLERK_AUDIENCE = "https://api.52aichan.com"

CLERK_JWT_PUBLIC_KEY = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv9e63a01GFJ+YJaUFv6r
kmyf/pCwsaBoo9gMWeTa935FW6fMMGAVHzQN7rI5ZRhePNL7ZvAveiZijk6fJDDp
X9lybfhUvuqLufyofyqUAEhl3NSN3bfDr1gmhT7q17ffST3mIDB5PeRX+0pLkvo4
rbcDRUa6UBOk0LQFGK4n5tqhN/d/bdmhuZSxtA1D1OOpZ7hPNkBeJ55ktJACkLJC
Dm4tho0SmUHNlIfpfArXmw2HAENWPBtwFQhg3GcBn8A67igT97jfv/suYTKXWRtI
1D9bOUe5x49tgmZvAsfodAz3SqKZP+nnvsGTId0LUbJIiZD4+g3btRzHSP7VOuLe
qQIDAQAB
-----END PUBLIC KEY-----
"""


CLERK_AUTH_PARTIES = [
    'https://52aichan.com',
    'http://52aichan.com',
    'https://www.52aichan.com',
    'http://www.52aichan.com',
    'https://api.52aichan.com',
    'http://api.52aichan.com',
    'http://localhost:3000',
    'http://localhost:8000',
]

FRONTEND_URL=config("FRONTEND_URL")

# Mixpanel Configuration
MIXPANEL_TOKEN = config("MIXPANEL_TOKEN", default="")
MIXPANEL_SECRET = config("MIXPANEL_SECRET", default="")
MIXPANEL_ENABLED = config("MIXPANEL_ENABLED", default=True, cast=bool)

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'django.contrib.humanize',
    # third party
    "django_htmx",
    "tailwind",
    "corsheaders",
    # internal
    "accounts",
    "storages",
    "channels",
    "rest_framework",
    "rest_framework.authtoken",
    #"sslserver", #remove before build
]

TAILWIND_APP_NAME="theme" # django-tailwind theme app
INTERNAL_IPS = [
    "0.0.0.0",
    "127.0.0.1",
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'helpers.myclerk.auth.ClerkAuthentication',
    ),
}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "cfehome.middleware.AdminAccessMiddleware",
    "helpers.myclerk.middleware.ClerkAuthMiddleware",
]

ROOT_URLCONF = "cfehome.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            TEMPLATE_DIR,
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "cfehome.wsgi.application"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DATABASE_URL = config('DATABASE_URL', default=None)
if DATABASE_URL is not None:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=60,  # Reduced from 600 to help avoid SSL timeouts
            conn_health_checks=True,  # Enable health checks
            ssl_require=True,  # If using SSL
        )
    }

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/


# nginx
MEDIA_URL = "media/"
MEDIA_ROOT = LOCAL_CDN / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# cloudinary video config
CLOUDINARY_CLOUD_NAME = config("CLOUDINARY_CLOUD_NAME", default="")
CLOUDINARY_PUBLIC_API_KEY = config("CLOUDINARY_PUBLIC_API_KEY", default="")
CLOUDINARY_SECRET_API_KEY= config("CLOUDINARY_SECRET_API_KEY")

# NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"  # Typical Windows path
NPM_BIN_PATH = "/usr/bin/npm"

# whitenoise/nginx
# STATIC_URL = "static/"
# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles-cdn'
# STATICFILES_DIRS= [
#     BASE_DIR / "staticfiles",
#     BASE_DIR / "theme/static",
# ]
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Make sure this is before the STATICFILES_STORAGE setting
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
# Ensure proper MIME types
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


from .cdn.conf import * # noqa

# Redis configuration
REDIS_HOST = config('REDIS_HOST')
REDIS_PORT = config('REDIS_PORT', default='12034')
REDIS_PASSWORD = config('REDIS_PASSWORD')
REDIS_URL = f'redis://default:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0'

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'USERNAME': 'default',
            'PASSWORD': REDIS_PASSWORD,
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'timeout': 20,
            },
            'MAX_CONNECTIONS': 1000,
        },
        'KEY_PREFIX': 'prod'
    }
}

# Use Redis for session storage
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_SECURE = True  # For development (use True in production)
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Base CSRF trusted origins
BASE_CSRF_TRUSTED_ORIGINS = [
    'https://52aichan.com',
    'http://52aichan.com',
    'https://www.52aichan.com',
    'http://www.52aichan.com',
    'https://*.52aichan.com',
    'http://*.52aichan.com',
    'http://localhost:3000',
    'http://localhost:8000',
]

# CORS settings
CORS_ALLOWED_ORIGINS = [
    'https://52aichan.com',
    'http://52aichan.com',
    'https://www.52aichan.com',
    'http://www.52aichan.com',
    'https://api.52aichan.com',
    'http://api.52aichan.com',
    'http://localhost:3000',
    'http://localhost:8000',
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-clerk-token',
    'referer',  # Add this
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']
CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "https://52aichan.com",
    "http://52aichan.com",
    "https://api.52aichan.com",
    "http://api.52aichan.com",
]
# Add this to allow requests without referer
CSRF_USE_SESSIONS = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
# Add these new settings
CSRF_COOKIE_DOMAIN = None
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_FAILURE_VIEW = 'django.views.csrf.csrf_failure'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True

# Cache time to live is 15 minutes
CACHE_TTL = 60 * 15
# Cache settings
CACHE_MIDDLEWARE_SECONDS = 60 * 15
CACHE_MIDDLEWARE_KEY_PREFIX = ''

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{asctime}] {levelname} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'goldmage.log',
            'formatter': 'simple',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'goldmage': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Login settings
LOGIN_URL = '/sign-in'  # Your actual login URL
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# HSTS Settings
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Admin email for error reporting
ADMIN_EMAIL = 'lungbridgestudio@gmail.com'  # Replace with your admin email