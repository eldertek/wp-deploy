import json
import os
from functools import lru_cache
from app import socketio
from werkzeug.security import check_password_hash, generate_password_hash

@lru_cache(maxsize=32)
def load_settings():
    config_path = "data/config.json"
    model_path = "data/settings.json"

    if not os.path.exists(config_path):
        try:
            with open(model_path, "r") as model_file:
                settings = json.load(model_file)
            save_settings(settings)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            socketio.emit(
                "error", f"Erreur lors du chargement des paramètres: {str(e)}"
            )
            return {}

    try:
        with open(config_path, "r") as config_file:
            return json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        socketio.emit(
            "error", f"Erreur lors du chargement de la configuration: {str(e)}"
        )
        return {}

def save_settings(settings):
    from .system import run_command
    run_command("chown www-data:www-data data", elevated=True)
    config_path = "data/config.json"
    try:
        with open(config_path, "w") as config_file:
            json.dump(settings, config_file, indent=4)
        run_command("chown www-data:www-data data/config.json", elevated=True)
    except Exception as e:
        socketio.emit("error", f"Erreur lors de la sauvegarde des paramètres: {str(e)}")

def verify_admin_credentials(username, password):
    users_file = "data/users.json"
    if not os.path.exists(users_file):
        return False
    with open(users_file, "r") as f:
        users = json.load(f)
    if username in users and check_password_hash(users[username], password):
        return True
    return False

def update_admin_password(username, new_password):
    users_file = "data/users.json"
    if not os.path.exists(users_file):
        users = {}
    else:
        with open(users_file, "r") as f:
            users = json.load(f)
    users[username] = generate_password_hash(new_password)
    try:
        with open(users_file, "w") as f:
            json.dump(users, f, indent=4)
        return True
    except Exception as e:
        socketio.emit("error", f"Erreur lors de la mise à jour du mot de passe: {str(e)}")
        return False

def load_sites_data():
    data_path = "data/sites_data.json"
    if os.path.exists(data_path):
        with open(data_path, "r") as f:
            return json.load(f)
    else:
        from .deployment import update_sites_data
        update_sites_data()
        return load_sites_data()

def save_sites_data(data):
    from .system import run_command
    data_path = "data/sites_data.json"
    run_command("chown www-data:www-data data", elevated=True)
    with open(data_path, "w") as f:
        json.dump(data, f, indent=4)
    run_command("chown www-data:www-data data/sites_data.json", elevated=True)