from flask_login import UserMixin
from werkzeug.security import generate_password_hash
import json

# Load settings to get the admin password
with open("data/settings.json", "r") as f:
    settings = json.load(f)
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
    from app import db
    admin_user = User.query.filter_by(username="admin").first()
    if admin_user:
        admin_user.password = generate_password_hash(new_password, method='sha256')
        db.session.commit()
