from flask_login import UserMixin
from app.utils import load_settings
from werkzeug.security import generate_password_hash
from app import db

# Load settings to get the admin password
settings = load_settings()
admin_password = settings.get("admin_password")

# In-memory storage for simplicity
users = {"admin": {"password": admin_password}}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

def load_user(user_id):
    return User(user_id)

def get_admin_password():
    return admin_password

def update_admin_password(new_password):
    admin_user = User.query.filter_by(username="admin").first()
    if admin_user:
        admin_user.password = generate_password_hash(new_password, method='sha256')
        db.session.commit()
