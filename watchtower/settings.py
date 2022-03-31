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
    except Exception as exc:
        if str(exc) == 'Incorrect padding':
            return value

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'g7+b)g5r@ugo4&ix$mto0b(u*^9_51p5a5-j#_@t)1g!fv&j99'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

DEPLOYMENT_INSTANCE = config('DEPLOYMENT_INSTANCE', default='local')

ALLOWED_HOSTS = [
    'watchtower.scibizinformatics.com',
    'localhost',
    '*'
]

# Application definition

INSTALLED_APPS=[
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django.contrib.admin',
    "django.contrib.postgres",
    "psqlextra",
    'dynamic_raw_id',
    'drf_yasg',
    'channels',
    'main',

    'smartbch',
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
        'PASSWORD': POSTGRES_PASSWORD,
        # 'OPTIONS': {
        #     'isolation_level': psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE,
        # }
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

DB_NUM = [0,1,2]
if DEPLOYMENT_INSTANCE == 'staging':
    DB_NUM = [3,4,5]

REDIS_HOST = decipher(config('REDIS_HOST'))
REDIS_PASSWORD = decipher(config('REDIS_PASSWORD'))
REDIS_PORT = decipher(config('REDIS_PORT'))
CELERY_IMPORTS = (
    'main.tasks',
    'smartbch.tasks',
)

CELERY_BROKER_URL = 'pyamqp://guest:guest@rabbitmq:5672//'
CELERY_RESULT_BACKEND = 'rpc://'

if REDIS_PASSWORD:
    # CELERY_BROKER_URL = 'redis://user:%s@%s:%s/%s' % (REDIS_PASSWORD, REDIS_HOST, REDIS_PORT, DB_NUM[0])
    # CELERY_RESULT_BACKEND = 'redis://user:%s@%s:%s/%s' % (REDIS_PASSWORD, REDIS_HOST, REDIS_PORT, DB_NUM[1])
    REDISKV = redis.StrictRedis(
        host=REDIS_HOST,
        password=REDIS_PASSWORD,
        port=6379,
        db=DB_NUM[2]
    )
else:
    # CELERY_BROKER_URL = 'redis://%s:%s/%s' % (REDIS_HOST, REDIS_PORT, DB_NUM[0])
    # CELERY_RESULT_BACKEND = 'redis://%s:%s/%s' % (REDIS_HOST, REDIS_PORT, DB_NUM[1])
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

TOKEN_IMAGES_DIR = config('TOKEN_IMAGES_DIR', default='/images')

CELERY_TASK_ACKS_LATE = True
CELERYD_PREFETCH_MULTIPLIER = 1
CELERYD_MAX_TASKS_PER_CHILD = 5



CELERY_BEAT_SCHEDULE = {
    'get_latest_block': {
        'task': 'main.tasks.get_latest_block',
        'schedule': 5
    },
    'manage_block_transactions': {
        'task': 'main.tasks.manage_block_transactions',
        'schedule': 7
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
    'parse_missing_records': {
        'task': 'smartbch.tasks.parse_missed_records_task',
        'schedule': 60 * 20 # run every 20 minutes.
    }
}

CORS_ALLOW_ALL_ORIGINS = True

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
}

SWAGGER_SETTINGS = {
    "SECURITY_SETTINGS": {},
    "SECURITY_DEFINITIONS": {}
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

#Telegram bot settings
# TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_BOT_TOKEN = "1764241013:AAGA5L8vuZf8CBJH3iHkFsp84pRbFzSGwrc"
TELEGRAM_BOT_USER = decipher(config('TELEGRAM_BOT_USER'))
TELEGRAM_DESTINATION_ADDR = decipher(config('TELEGRAM_DESTINATION_ADDR'))


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
        'django.template': {
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
