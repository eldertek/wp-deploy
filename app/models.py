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
