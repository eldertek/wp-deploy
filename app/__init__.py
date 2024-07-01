from flask import Flask
from flask_login import LoginManager
import os

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config.from_object('app.config.Config')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'routes.login'

login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "info"

from app import routes
