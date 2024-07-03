from flask_login import UserMixin
from app.utils import load_settings

# Load settings to get the admin password
settings = load_settings()
admin_password = settings.get('admin_password')

# In-memory storage for simplicity
users = {'admin': {'password': admin_password}}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

def load_user(user_id):
    return User(user_id)

def update_admin_password(new_password):
    users['admin']['password'] = new_password

def create_admin_user():
    users['admin'] = {'password': admin_password}
