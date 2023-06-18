"""
Django settings for x project.

Generated by 'django-admin startproject' using Django 3.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
from decouple import config
import redis
import psycopg2
from datetime import timedelta
import base64
import decimal

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def safe_cast(value, var_type=str, default=None):
    try:
        return var_type(value)
    except Exception:
        return default


def decipher(value):
    try:
        return base64.b64decode(value.encode()).decode()
    except:
        return value


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'g7+b)g5r@ugo4&ix$mto0b(u*^9_51p5a5-j#_@t)1g!fv&j99'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
DEPLOYMENT_INSTANCE = config('DEPLOYMENT_INSTANCE', default='prod')
DOMAIN = 'https://watchtower.cash'

if DEPLOYMENT_INSTANCE == 'local':
    DEBUG = True
    DOMAIN = 'http://localhost:8000'

ALLOWED_HOSTS = [
    '*'
]

# Application definition

INSTALLED_APPS=[
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'constance.backends.database',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django.contrib.admin',
    "django.contrib.postgres",
    "psqlextra",
    'dynamic_raw_id',
    'drf_yasg',
    'channels',
    'push_notifications',
    'django_filters',

    'constance',
    'main',
    'smartbch',
    'paytacapos',
    'anyhedge',
    'chat',
    'notifications',
    'jpp',
    'ramp'
]

MIDDLEWARE=[
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'watchtower.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'watchtower.wsgi.application'
ASGI_APPLICATION = 'watchtower.asgi.application'

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

POSTGRES_DB = decipher(config('POSTGRES_DB'))
POSTGRES_HOST = decipher(config('POSTGRES_HOST'))
POSTGRES_PORT = decipher(config('POSTGRES_PORT'))
POSTGRES_USER = decipher(config('POSTGRES_USER'))
POSTGRES_PASSWORD = decipher(config('POSTGRES_PASSWORD'))

DATABASES = {
    'default': {
        'ENGINE': 'psqlextra.backend',
        'NAME': POSTGRES_DB,
        'HOST': POSTGRES_HOST,
        'PORT': POSTGRES_PORT,
        'USER': POSTGRES_USER,
        'PASSWORD': POSTGRES_PASSWORD
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Django constance
# For dynamic settings
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'
CONSTANCE_CONFIG = {
    'P2P_SETTLEMENT_SERVICE_FEE': (
        0, 'Settlement service fee for contracts settled by watchtower',
    ),
    'P2P_SETTLEMENT_SERVICE_FEE_ADDRESS': (
        '', 'Recipient of settlement service fee of contracts settled by watchtower',
    ),
    'GP_LP_SERVICE_FEE': (
        0, 'Service fee for contracts created with BCH bull(General Protocol LP)',
    ),
    'GP_LP_SERVICE_FEE_ADDRESS': (
        '', 'Service fee address for contracts created with BCH bull(General Protocol LP)',
    ),
    'GP_LP_SERVICE_FEE_NAME': (
        'Paytaca fee', 'Service fee name displayed for contracts created with BCH bull(General Protocol LP)',
    ),
    'GP_LP_SERVICE_FEE_DESCRIPTION': (
        '', 'Service fee name displayed for contracts created with BCH bull(General Protocol LP)',
    ),
}
CONSTANCE_CONFIG_FIELDSETS = {
    'Anyhedge (P2P)': (
        'P2P_SETTLEMENT_SERVICE_FEE',
        'P2P_SETTLEMENT_SERVICE_FEE_ADDRESS',
    ),
    'Anyhedge (BCH Bull)': (
        'GP_LP_SERVICE_FEE',
        'GP_LP_SERVICE_FEE_ADDRESS',
        'GP_LP_SERVICE_FEE_NAME',
        'GP_LP_SERVICE_FEE_DESCRIPTION',
    ),
}


# Push notifications (django-push-notifications)
# See https://github.com/jazzband/django-push-notifications
PUSH_NOTIFICATIONS_SETTINGS = {
    # For Firebase (Android)
    # -----------------------------------------
    "FCM_API_KEY": config("FIREBASE_API_KEY"),

    # For Google cloud messaging (Android)
    # -----------------------------------------
    # "GCM_API_KEY": "[your api key]",

    # For Apple Push Notification Services (IOS)
    # -----------------------------------------
    "APNS_CERTIFICATE": os.path.join(BASE_DIR, config('APNS_CERTIFICATE_PATH', 'certificate.pem')),
    "APNS_AUTH_KEY_ID": config('APNS_AUTH_KEY_ID', None),
    "APNS_TEAM_ID": config('APNS_TEAM_ID', None),
    "APNS_USE_ALTERNATIVE_PORT": config('APNS_USE_ALTERNATIVE_PORT', None),
    "APNS_TOPIC": config('APNS_TOPIC', None),

    # For Webpush
    # -----------------------------------------
    # "WNS_PACKAGE_SECURITY_ID": "[your package security id, e.g: 'ms-app://e-3-4-6234...']",
    # "WNS_SECRET_KEY": "[your app secret key, e.g.: 'KDiejnLKDUWodsjmewuSZkk']",
    # "WP_PRIVATE_KEY": "/path/to/your/private.pem",
    # "WP_CLAIMS": {'sub': "mailto: development@example.com"}
}


DB_NUM = [3,4,5]
if DEPLOYMENT_INSTANCE == 'prod':
    DB_NUM = [0,1,2]

REDIS_HOST = decipher(config('REDIS_HOST'))
REDIS_PASSWORD = decipher(config('REDIS_PASSWORD'))
REDIS_PORT = decipher(config('REDIS_PORT'))
CELERY_IMPORTS = (
    'main.tasks',
    'smartbch.tasks',
    'anyhedge.tasks',
    'ramp.tasks'
)

# CELERY_BROKER_URL = 'pyamqp://guest:guest@rabbitmq:5672//'
# CELERY_RESULT_BACKEND = 'rpc://'

if REDIS_PASSWORD:
    redis_prefix = ''
    if DEPLOYMENT_INSTANCE == 'prod':
        redis_prefix = 'user'
        
    CELERY_BROKER_URL = 'redis://%s:%s@%s:%s/%s' % (redis_prefix, REDIS_PASSWORD, REDIS_HOST, REDIS_PORT, DB_NUM[0])
    CELERY_RESULT_BACKEND = 'redis://%s:%s@%s:%s/%s' % (redis_prefix, REDIS_PASSWORD, REDIS_HOST, REDIS_PORT, DB_NUM[1])
    REDISKV = redis.StrictRedis(
        host=REDIS_HOST,
        password=REDIS_PASSWORD,
        port=6379,
        db=DB_NUM[2]
    )
else:
    CELERY_BROKER_URL = 'redis://%s:%s/%s' % (REDIS_HOST, REDIS_PORT, DB_NUM[0])
    CELERY_RESULT_BACKEND = 'redis://%s:%s/%s' % (REDIS_HOST, REDIS_PORT, DB_NUM[1])
    REDISKV = redis.StrictRedis(
        host=REDIS_HOST,
        port=6379,
        db=DB_NUM[2]
    )

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

TOKEN_IMAGES_DIR = config('TOKEN_IMAGES_DIR', default='/images')

CELERY_TASK_ACKS_LATE = True
CELERYD_PREFETCH_MULTIPLIER = 1
CELERYD_MAX_TASKS_PER_CHILD = 5



CELERY_BEAT_SCHEDULE = {
    'update_oracle_prices': {
        'task': 'anyhedge.tasks.check_new_price_messages',
        'schedule': 60,
    },
    'update_anyhedge_contract_settlements': {
        'task': 'anyhedge.tasks.update_matured_contracts',
        'schedule': 60,
    },
    'update_anyhedge_contracts_for_liquidation': {
        'task': 'anyhedge.tasks.update_contracts_for_liquidation',
        'schedule': 120,
    },
    'parse_contracts_liquidity_fee': {
        'task': 'anyhedge.tasks.parse_contracts_liquidity_fee',
        'schedule': 5 * 60,
    },
    'get_latest_block': {
        'task': 'main.tasks.get_latest_block',
        'schedule': 5
    },
    'manage_blocks': {
        'task': 'main.tasks.manage_blocks',
        'schedule': 7
    },
    'find_wallet_history_missing_tx_timestamps': {
        'task': 'main.tasks.find_wallet_history_missing_tx_timestamps',
        'schedule': 60 * 2,
    },
    'resolve_wallet_history_usd_values': {
        'task': 'main.tasks.resolve_wallet_history_usd_values',
        'schedule': 60 * 2,
    },
    'fetch_latest_usd_price': {
        'task': 'main.tasks.fetch_latest_usd_price',
        'schedule': 60 * 2,
    },
    'preload_smartbch_blocks': {
        'task': 'smartbch.tasks.preload_new_blocks_task',
        'schedule': 20,
    },
    'parse_new_smartbch_blocks': {
        'task': 'smartbch.tasks.parse_blocks_task',
        'schedule': 30,
    },
    'parse_token_contract_metadata': {
        'task': 'smartbch.tasks.parse_token_contract_metadata_task',
        'schedule': 300,
    },
    'save_token_icons': {
        'task': 'smartbch.tasks.save_token_icons_task',
        'schedule': 300,
    },
    'parse_missing_records': {
        'task': 'smartbch.tasks.parse_missed_records_task',
        'schedule': 60 * 20 # run every 20 minutes.
    },
    'update_shift_status': {
        'task': 'ramp.tasks.update_shift_status',
        'schedule': 60
    }
}

from corsheaders.defaults import default_headers
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-paypro-version",
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    # Parser classes priority-wise for Swagger
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer'
    ]
}

SWAGGER_SETTINGS = {
    "SECURITY_SETTINGS": {},
    "SECURITY_DEFINITIONS": {}
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

#Telegram bot settings
# TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
# TELEGRAM_BOT_TOKEN = "1764241013:AAGA5L8vuZf8CBJH3iHkFsp84pRbFzSGwrc"
# TELEGRAM_BOT_USER = decipher(config('TELEGRAM_BOT_USER'))
# TELEGRAM_DESTINATION_ADDR = decipher(config('TELEGRAM_DESTINATION_ADDR'))


# Slack credentials and configurations

SLACK_BOT_USER_TOKEN = config('SLACK_BOT_USER_TOKEN')
SLACK_VERIFICATION_TOKEN = config('SLACK_VERIFICATION_TOKEN')
SLACK_CLIENT_ID = config('SLACK_CLIENT_ID')
SLACK_CLIENT_SECRET = config('SLACK_CLIENT_SECRET')
SLACK_SIGNING_SECRET = config('SLACK_SIGNING_SECRET')

SLACK_DESTINATION_ADDR = 'https://watchtower.scibizinformatics.com/slack/notify/'
SLACK_THEME_COLOR = '#82E0AA'


MAX_BLOCK_TRANSACTIONS = 500
MAX_BLOCK_AWAY = 4000
MAX_RESTB_RETRIES = 14
MAX_SLPBITCOIN_SOCKET_DURATION = 10
MAX_BITSOCKET_DURATION = 10
BITDB_QUERY_LIMIT_PER_PAGE = 1000
TRANSACTIONS_PER_CHUNK=100

# Sideshift credentials
SIDESHIFT_SECRET_KEY = config('SIDESHIFT_SECRET_KEY')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '[%(asctime)s %(name)s] %(levelname)s [%(pathname)s:%(lineno)d] - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console'
        },
    },
    'loggers': {
        '': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'main': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'chat': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'django.template': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'ramp': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False    
        }
    },
}

REDIS_CHANNEL_DB = [0, 1][DEPLOYMENT_INSTANCE == 'prod']
REDIS_CHANNEL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_CHANNEL_DB}"

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_CHANNEL]
        }
    }
}


# websocket vars
WATCH_ROOM = 'watch_room'

START_BLOCK = int(decipher(config('START_BLOCK')))


SMARTBCH = {
    "START_BLOCK": safe_cast(
        decipher(config('SBCH_START_BLOCK', None)),
        var_type=decimal.Decimal,
        default=None,
    ),
    "BLOCK_TO_PRELOAD": safe_cast(
        decipher(config('SBCH_BLOCK_TO_PRELOAD', None)),
        var_type=int,
        default=None,
    ),
    "BLOCKS_PER_TASK": safe_cast(
        decipher(config('SBCH_BLOCKS_PER_TASK', 50)),
        var_type=int,
        default=50,
    ),
}


PAYTACAPOS = {
    "TOTP_SECRET_KEY": decipher(config('TOTP_SECRET_KEY')),
}

ANYHEDGE = {
    "ANYHEDGE_LP_BASE_URL": config("ANYHEDGE_LP_BASE_URL", "https://staging-liquidity.anyhedge.com"),
    "ANYHEDGE_DEFAULT_ORACLE_RELAY": config("ANYHEDGE_DEFAULT_ORACLE_RELAY", ""),
    "ANYHEDGE_DEFAULT_ORACLE_PORT": config("ANYHEDGE_DEFAULT_ORACLE_PORT", 0),
    "ANYHEDGE_DEFAULT_ORACLE_PUBKEY": config("ANYHEDGE_DEFAULT_ORACLE_PUBKEY", ""),
    "ANYHEDGE_SETTLEMENT_SERVICE_AUTH_TOKEN": config("ANYHEDGE_SETTLEMENT_SERVICE_AUTH_TOKEN", ""),
}


BCH_NETWORK = config('BCH_NETWORK', default='chipnet')
RPC_USER = decipher(config('RPC_USER'))

BCHN_HOST = config('BCHN_CHIPNET_HOST', 'bchn')
if BCH_NETWORK == 'mainnet':
    BCHN_HOST = config('BCHN_MAINNET_HOST', 'bchn')
BCHN_RPC_PASSWORD = decipher(config('BCHN_RPC_PASSWORD'))

BCHN_NODE = f'http://{RPC_USER}:{BCHN_RPC_PASSWORD}@{BCHN_HOST}:8332'

# BCHD_RPC_PASSWORD = decipher(config('BCHD_RPC_PASSWORD'))
# BCHD_NODE = f'http://{RPC_USER}:{BCHD_RPC_PASSWORD}@bchd:18334'
BCHD_NODE = 'bchd.paytaca.com:8335'

WT_DEFAULT_CASHTOKEN_ID = 'wt_cashtoken_token_id'

bcmr_url_type = ''
if BCH_NETWORK == 'chipnet':
    bcmr_url_type = f'-chipnet'

PAYTACA_BCMR_URL = f'https://bcmr{bcmr_url_type}.paytaca.com/api'
