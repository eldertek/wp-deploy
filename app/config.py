import os
import json


class Config:
    SECRET_KEY_FILE = "data/secret_key.json"

    if not os.path.exists(SECRET_KEY_FILE):
        secret_key = os.urandom(24).hex()
        with open(SECRET_KEY_FILE, "w") as f:
            json.dump({"secret_key": secret_key}, f)
    else:
        with open(SECRET_KEY_FILE, "r") as f:
            secret_key = json.load(f)["secret_key"]

    SECRET_KEY = secret_key
