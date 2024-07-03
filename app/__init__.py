from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
import os
import json
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import atexit

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config.from_object('app.config.Config')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "info"

socketio = SocketIO(app, cors_allowed_origins="*")

def deploy_all_websites():
    from app.utils import deploy_static, log_deployment
    start_time = datetime.datetime.now()
    domains = [domain for domain in os.listdir('/var/www/') if os.path.isdir(os.path.join('/var/www/', domain)) and not domain.startswith('.')]
    for domain in domains:
        success = deploy_static(domain)
        duration = (datetime.datetime.now() - start_time).total_seconds()
        log_deployment(domain, success, duration)

def update_site_data():
    from app.utils import save_site_data
    save_site_data()

scheduler = BackgroundScheduler()
scheduler.add_job(deploy_all_websites, 'cron', hour=0, minute=0)
scheduler.add_job(update_site_data, 'interval', minutes=10)
scheduler.start()

# Ensure the scheduler is shut down when exiting the app
atexit.register(lambda: scheduler.shutdown())

from app import routes

if __name__ == '__main__':
    socketio.run(app, debug=False)
