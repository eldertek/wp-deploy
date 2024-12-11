"""
Gunicorn configuration file.
"""

bind = "127.0.0.1:8000"
workers = 3
limit_upload = 50 * 1024 * 1024 * 1024
timeout = 3600

# Log configuration
errorlog = '/var/log/wp-deploy/error.log'
accesslog = '/var/log/wp-deploy/access.log'
loglevel = 'info'