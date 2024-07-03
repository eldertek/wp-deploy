import os
import json
from werkzeug.security import generate_password_hash, check_password_hash

class Config:
    SECRET_KEY_FILE = "data/secret_key.json"
    USERS_FILE = "data/users.json"

    if not os.path.exists(SECRET_KEY_FILE):
        secret_key = os.urandom(24).hex()
        with open(SECRET_KEY_FILE, "w") as f:
            json.dump({"secret_key": secret_key}, f)
    else:
        with open(SECRET_KEY_FILE, "r") as f:
            secret_key = json.load(f)["secret_key"]

    SECRET_KEY = secret_key

    # Ensure default admin credentials are set in users.json
    if not os.path.exists(USERS_FILE):
        users = {
            "admin": generate_password_hash("adminpass")
        }
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)
    else:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
            if "admin" not in users or not check_password_hash(users["admin"], "adminpass"):
                users["admin"] = generate_password_hash("adminpass")
            with open(USERS_FILE, "w") as f:
                json.dump(users, f, indent=4)
