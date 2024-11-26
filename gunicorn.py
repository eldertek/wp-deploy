"""
Gunicorn configuration file.
"""

BIND = "127.0.0.1:8000"
WORKERS = 3
LIMIT_UPLOAD = 50 * 1024 * 1024 * 1024
TIMEOUT = 3600

ERRORLOG = '/var/log/wp-deploy/error.log'
ACCESSLOG = '/var/log/wp-deploy/access.log'
LOGLEVEL = 'info'