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

# Temp file configuration
worker_tmp_dir = '/var/tmp/gunicorn'
tmp_upload_dir = '/var/tmp/gunicorn'

# Cleanup configuration
clean_workers_tmp = True