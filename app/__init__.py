from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
import os
import json

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config.from_object('app.config.Config')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'routes.login'

login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "info"

socketio = SocketIO(app, cors_allowed_origins="*")

from app import routes

def load_settings():
    config_path = 'app/config.json'
    model_path = 'app/settings.json'
    
    if not os.path.exists(config_path):
        with open(model_path, 'r') as model_file:
            settings = json.load(model_file)
        save_settings(settings)
        
    if os.path.exists(config_path):
        with open(config_path, 'r') as config_file:
            return json.load(config_file)
    else:
        return {}

def save_settings(settings):
    config_path = 'app/config.json'
    with open(config_path, 'w') as config_file:
        json.dump(settings, config_file, indent=4)

if __name__ == '__main__':
    socketio.run(app, debug=True)
