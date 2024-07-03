from flask_login import UserMixin
from app import login_manager
import json

class User(UserMixin):
    def __init__(self, id):
        self.id = id

    @staticmethod
    def get(user_id):
        with open("data/users.json", "r") as f:
            users = json.load(f)
        if user_id in users:
            return User(user_id)
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)
