import os
import json
import datetime
import requests
from app import socketio
from .system import run_command
from .wordpress import get_published_articles
from .settings import save_sites_data

def deploy_static(domain_name):
    start_time = datetime.datetime.now()
    try:
        wp_path = f"/var/www/{domain_name}"
        static_path = f"{wp_path}/wp-content/uploads/simply-static/temp-files/"
        destination_path = f"/var/www/{domain_name}-static"

        socketio.emit("message", f"Début du déploiement pour {domain_name}.")

        # Supprimer les fichiers temporaires
        if os.path.exists(static_path):
            socketio.emit("console", "Suppression des fichiers temporaires.")
            if not run_command(f"rm -rf {static_path}", elevated=True):
                raise Exception("Failed to remove static path")

        # Force Elementor data update
        try:
            socketio.emit("console", "Mise à jour de la base de données Elementor.")
            run_command(f"wp elementor update db --path={wp_path}")
        except Exception as e:
            if "is not a registered wp command" in str(e):
                socketio.emit("console", "Elementor command not found, skipping Elementor data update.")
            else:
                raise Exception("Failed to update Elementor data")

        # Try to activate Simply Static plugin
        try:
            socketio.emit("console", "Activation du plugin Simply Static.")
            result = run_command(f"wp plugin activate simply-static --path={wp_path}", return_output=True)
            socketio.emit("console", f"Activation de Simply Static: {result}")
            result = run_command(f"wp plugin activate simply-static-pro --path={wp_path}", return_output=True)
            socketio.emit("console", f"Activation de Simply Static Pro: {result}")
        except Exception:
            socketio.emit("console", "Erreur lors de l'activation des plugins, mais on continue.")

        # Run Simply Static export
        socketio.emit("console", "Exécution de l'exportation Simply Static.")
        result = run_command(f"wp simply-static run --path={wp_path}", return_output=True)  # Store result
        if "Success: Export Completed" in result:
            socketio.emit("console", "Exportation réussie.")
            # Move the first zip file in static path to the destination and copy content if folder exists
            zip_files = [f for f in os.listdir(static_path) if f.endswith(".zip")]
            if zip_files:
                first_zip = zip_files[0]
                socketio.emit("console", f"Déplacement de {first_zip} vers le répertoire de destination.")

                # Ensure the destination path exists and set permissions
                if not os.path.exists(destination_path):
                    socketio.emit("console", "Création du répertoire de destination.")
                    if not run_command(f"mkdir -p {destination_path}", elevated=True):
                        raise Exception("Failed to create destination path")
                    if not run_command(f"chown -R www-data:www-data {destination_path}", elevated=True):
                        raise Exception("Failed to change ownership of destination path")

                # Unzip the file to the destination path
                if not run_command(f"unzip -o {os.path.join(static_path, first_zip)} -d {destination_path}"):
                    raise Exception("Failed to unzip file to destination path")

                # Set ownership of the destination path to www-data
                if not run_command(f"chown -R www-data:www-data {destination_path}", elevated=True):
                    raise Exception("Failed to change ownership of destination path to www-data")

                # Create Readme.md with deployment details
                readme_content = f"# Deployment Info\n\nDomain: {domain_name}\n\nDate: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                with open(os.path.join(destination_path, "Readme.md"), "w") as readme_file:
                    readme_file.write(readme_content)

                socketio.emit("console", "Création de Readme.md avec les détails du déploiement.")

                # Clear the static path
                if not run_command(f"rm -rf {static_path}"):
                    raise Exception("Failed to clear static path")

                socketio.emit("success", f"Déploiement réussi pour {domain_name}.")
                success = True
            else:
                socketio.emit("error", f"Aucun fichier ZIP trouvé dans {static_path}.")
                success = False
        else:
            socketio.emit("error", f"Erreur lors de l'exportation Simply Static: {result}")
            success = False

        duration = (datetime.datetime.now() - start_time).total_seconds()
        log_deployment(domain_name, success, duration)
        return success
    except Exception as e:
        socketio.emit(
            "error", f"Erreur lors du déploiement statique pour {domain_name}: {str(e)}"
        )
        log_deployment(domain_name, False, 0)
        return False

def log_deployment(domain_name, success, duration):
    log_entry = {
        "domain": domain_name,
        "success": success,
        "timestamp": int(datetime.datetime.now().timestamp()),
        "time": datetime.datetime.now().strftime('%d/%m/%Y - %Hh%M'),
        "duration": round(duration, 2),
    }
    log_path = "data/deployments.json"
    run_command("chown www-data:www-data data", elevated=True)
    if os.path.exists(log_path):
        with open(log_path, "r") as log_file:
            logs = json.load(log_file)
    else:
        logs = []
    logs.append(log_entry)
    with open(log_path, "w") as log_file:
        json.dump(logs, log_file, indent=4)
    run_command(
        "chown www-data:www-data data/deployments.json", elevated=True
    )  # Ensure ownership

def get_indexed_articles(domain_name):
    api_key = "33cef647-1f76-4604-927d-e7f0d5b93205"
    url = f"https://api.spaceserp.com/google/search?apiKey={api_key}&q=site%3A{domain_name}&location=Lyon%2CAuvergne-Rhone-Alpes%2CFrance&domain=google.fr&gl=fr&hl=fr&resultFormat=json&resultBlocks=total_results_count"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("total_results_count", 0)
    return 0

def check_site_status(domain):
    try:
        response = requests.get(f"https://bo.{domain}/wp-json")
        return response.status_code == 200
    except Exception:
        return False

def update_sites_data(indexed=False):
    data_path = "data/sites_data.json"
    if os.path.exists(data_path):
        with open(data_path, "r") as f:
            sites_data = json.load(f)
    else:
        sites_data = {"sites": []}

    existing_domains = {site["domain"]: site for site in sites_data["sites"]}

    domains = [
        domain for domain in os.listdir("/var/www/")
        if os.path.isdir(os.path.join("/var/www/", domain)) and not domain.startswith(".") and not domain.endswith("-static")
    ]

    for domain in domains:
        published_articles = get_published_articles(domain)
        if indexed:
            indexed_articles = get_indexed_articles(domain)
            indexed_percentage = (indexed_articles / published_articles * 100) if published_articles > 0 else 0
        else:
            indexed_articles = existing_domains.get(domain, {}).get("indexed_articles", 0)
            indexed_percentage = existing_domains.get(domain, {}).get("indexed_percentage", 0)

        status = "online" if check_site_status(domain) else "offline"

        existing_domains[domain] = {
            "domain": domain,
            "published_articles": published_articles,
            "indexed_articles": indexed_articles,
            "indexed_percentage": round(indexed_percentage, 2),
            "status": status,
            "category": existing_domains.get(domain, {}).get("category", "Aucune catégorie"),
            "language": existing_domains.get(domain, {}).get("language", "Aucune langue")
        }

    sites_data["sites"] = list(existing_domains.values())
    sites_data['last_update'] = datetime.datetime.now().strftime("%d/%m/%Y - %Hh%M")
    save_sites_data(sites_data)