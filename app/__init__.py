from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
import atexit

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config.from_object('app.config.Config')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "info"

socketio = SocketIO(app, cors_allowed_origins="*")

from app.models import User
from app.utils.jobs import create_scheduler, start_scheduler, shutdown_scheduler

# Create and start the scheduler
scheduler = create_scheduler()
start_scheduler()

# Register the shutdown function
atexit.register(shutdown_scheduler)

# Expose the scheduler to be used in routes
app.scheduler = scheduler

from app import routes

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

if __name__ == '__main__':
    socketio.run(app, debug=False)