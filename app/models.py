from flask_login import UserMixin

# In-memory storage for simplicity
users = {'admin': {'password': 'password'}}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

def load_user(user_id):
    return User(user_id)
