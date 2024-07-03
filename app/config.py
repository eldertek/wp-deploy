import os
import json
from werkzeug.security import generate_password_hash


class Config:
    SECRET_KEY_FILE = "data/secret_key.json"
    SETTINGS_FILE = "data/settings.json"

    if not os.path.exists(SECRET_KEY_FILE):
        secret_key = os.urandom(24).hex()
        with open(SECRET_KEY_FILE, "w") as f:
            json.dump({"secret_key": secret_key}, f)
    else:
        with open(SECRET_KEY_FILE, "r") as f:
            secret_key = json.load(f)["secret_key"]

    SECRET_KEY = secret_key

    # Ensure default admin credentials are set in settings.json
    if not os.path.exists(SETTINGS_FILE):
        settings = {
            "admin_username": "admin",
            "admin_password": generate_password_hash("admin")
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    else:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            if "admin_username" not in settings:
                settings["admin_username"] = "admin"
            if "admin_password" not in settings or not settings["admin_password"].startswith("pbkdf2:sha256:"):
                settings["admin_password"] = generate_password_hash("admin")
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=4)
