from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
import os
import json
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import atexit
import logging
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash
from app.models import User, db, update_admin_password, get_admin_password

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config.from_object("app.config.Config")

# Ajout du middleware ProxyFix pour gérer les en-têtes de proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "info"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")

def create_admin_user():
    admin_username = "admin"
    admin_password = get_admin_password()  # Utiliser le mot de passe admin des paramètres

    if not User.query.filter_by(username=admin_username).first():
        admin_user = User(
            username=admin_username,
            password=generate_password_hash(admin_password, method='sha256'),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        logger.info("Admin user created.")
    else:
        # Mettre à jour le mot de passe de l'utilisateur admin existant
        update_admin_password(admin_password)
        logger.info("Admin user already exists and password updated.")

create_admin_user()

def deploy_all_websites():
    from app.utils import deploy_static, log_deployment

    start_time = datetime.datetime.now()
    try:
        domains = [
            domain
            for domain in os.listdir("/var/www/")
            if os.path.isdir(os.path.join("/var/www/", domain))
            and not domain.startswith(".")
        ]
        for domain in domains:
            try:
                success = deploy_static(domain)
                duration = (datetime.datetime.now() - start_time).total_seconds()
                log_deployment(domain, success, duration)
            except Exception as e:
                logger.error(f"Erreur lors du déploiement de {domain}: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur lors du déploiement de tous les sites: {str(e)}")


def update_site_data():
    from app.utils import save_site_data

    try:
        save_site_data()
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des données du site: {str(e)}")


scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(
    deploy_all_websites, "cron", hour=0, minute=0, misfire_grace_time=3600
)
scheduler.add_job(update_site_data, "interval", minutes=10, misfire_grace_time=300)

try:
    scheduler.start()
except Exception as e:
    logger.error(f"Erreur lors du démarrage du planificateur: {str(e)}")

# Ensure the scheduler is shut down when exiting the app
atexit.register(lambda: scheduler.shutdown(wait=False))

from app import routes

if __name__ == "__main__":
    socketio.run(app, debug=False, use_reloader=False)
