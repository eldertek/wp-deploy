import json
import os
from app import socketio
from werkzeug.security import check_password_hash, generate_password_hash

def load_settings():
    config_path = "data/config.json"
    try:
        with open(config_path, "r") as config_file:
            settings = json.load(config_file)
            # Ensure the new setting has a default value if not present
            if "wordpress_admin_email" not in settings:
                settings["wordpress_admin_email"] = "admin@example.com"
            if "test_mode" not in settings:
                settings["test_mode"] = False
            return settings
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
    default_data = {
        "sites": [],
        "last_update": ""
    }
    
    try:
        if os.path.exists(data_path):
            with open(data_path, "r") as f:
                data = json.load(f)
                # Vérifier si le format est correct
                if not isinstance(data, dict) or "sites" not in data:
                    raise ValueError("Invalid data format")
                return data
    except (json.JSONDecodeError, ValueError) as e:
        socketio.emit("console", f"Réinitialisation du fichier sites_data.json : {str(e)}")
        # Si le fichier est corrompu ou vide, on le réinitialise avec la structure de base
        save_sites_data(default_data)
        return default_data
    except Exception as e:
        socketio.emit("error", f"Erreur lors du chargement des données des sites: {str(e)}")
        return default_data

    # Si le fichier n'existe pas, on le crée avec la structure de base
    save_sites_data(default_data)
    return default_data

def save_sites_data(data):
    from .system import run_command
    data_path = "data/sites_data.json"
    run_command("chown www-data:www-data data", elevated=True)
    with open(data_path, "w") as f:
        json.dump(data, f, indent=4)
    run_command("chown www-data:www-data data/sites_data.json", elevated=True)

def load_categories():
    categories_path = "data/categories.json"
    default_category = "Aucune catégorie"
    if os.path.exists(categories_path):
        with open(categories_path, "r") as f:
            categories = json.load(f)
    else:
        categories = []

    if default_category not in categories:
        categories.append(default_category)
        save_categories(categories) 

    return categories

def save_categories(categories):
    categories_path = "data/categories.json"
    with open(categories_path, "w") as f:
        json.dump(categories, f, indent=4)

def load_languages():
    languages_path = "data/languages.json"
    default_language = "Aucune langue"  # Ajout de la langue par défaut
    if os.path.exists(languages_path):
        with open(languages_path, "r") as f:
            languages = json.load(f)
    else:
        languages = []

    if default_language not in languages:
        languages.append(default_language)
        save_languages(languages)  # Sauvegarde des langues avec la langue par défaut

    return languages

def save_languages(languages):
    languages_path = "data/languages.json"
    with open(languages_path, "w") as f:
        json.dump(languages, f, indent=4)