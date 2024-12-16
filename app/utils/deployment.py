import os
import json
import datetime
import requests
from app import socketio
from .system import run_command
from .wordpress import get_published_articles
from .settings import load_sites_data, save_sites_data

def deploy_static(domain_name):
    start_time = datetime.datetime.now()
    try:
        # Verify paths before proceeding
        if not verify_paths(domain_name):
            raise Exception("Path verification failed")
            
        # Resolve the real paths
        base_path = os.path.realpath("/var/www")
        wp_path = os.path.join(base_path, domain_name)
        static_path = os.path.join(wp_path, "wp-content/uploads/staatic/deploy/")
        staging_path = os.path.join(wp_path, "wp-content/uploads/staatic/staging/")
        destination_path = os.path.join("/var/www/static", domain_name)
        tmp_static_path = os.path.join("/mnt/disk2/tmpstatic", domain_name)
        tmp_staging_path = os.path.join("/mnt/disk2/staging", domain_name)

        socketio.emit("message", f"Début du déploiement pour {domain_name}.")

        # Créer et configurer les répertoires temporaires principaux si nécessaire
        for tmp_dir in ["/mnt/disk2/tmpstatic", "/mnt/disk2/staging"]:
            if not os.path.exists(tmp_dir):
                if not run_command(f"mkdir -p {tmp_dir}", elevated=True):
                    raise Exception(f"Failed to create temporary directory: {tmp_dir}")
                # Set permissions on main temp directories
                if not run_command(f"chown www-data:www-data {tmp_dir}", elevated=True):
                    raise Exception(f"Failed to set ownership on temporary directory: {tmp_dir}")
                if not run_command(f"chmod 755 {tmp_dir}", elevated=True):
                    raise Exception(f"Failed to set permissions on temporary directory: {tmp_dir}")

        # Supprimer l'ancien lien symbolique deploy et le répertoire temporaire s'ils existent
        if os.path.exists(static_path):
            socketio.emit("console", "Suppression de l'ancien lien symbolique deploy.")
            if not run_command(f"rm -rf {static_path}", elevated=True):
                raise Exception("Failed to remove old deploy symlink")
        if os.path.exists(tmp_static_path):
            if not run_command(f"rm -rf {tmp_static_path}", elevated=True):
                raise Exception("Failed to remove old temporary deploy directory")

        # Configurer le répertoire de staging seulement s'il existe et n'est pas un lien symbolique
        if os.path.exists(staging_path) and not os.path.islink(staging_path):
            socketio.emit("console", "Configuration du répertoire de staging.")
            if not run_command(f"rm -rf {staging_path}", elevated=True):
                raise Exception("Failed to remove old staging directory")
        
        # Créer le répertoire de staging temporaire s'il n'existe pas
        if not os.path.exists(tmp_staging_path):
            if not run_command(f"mkdir -p {tmp_staging_path}", elevated=True):
                raise Exception("Failed to create staging temporary directory")
            if not run_command(f"chown www-data:www-data {tmp_staging_path}", elevated=True):
                raise Exception("Failed to set ownership on staging temporary directory")
            if not run_command(f"chmod 755 {tmp_staging_path}", elevated=True):
                raise Exception("Failed to set permissions on staging temporary directory")

        # Créer le répertoire temporaire deploy
        if not run_command(f"mkdir -p {tmp_static_path}", elevated=True):
            raise Exception("Failed to create deploy temporary directory")
        if not run_command(f"chown www-data:www-data {tmp_static_path}", elevated=True):
            raise Exception("Failed to set ownership on deploy temporary directory")
        if not run_command(f"chmod 755 {tmp_static_path}", elevated=True):
            raise Exception("Failed to set permissions on deploy temporary directory")

        # Créer les liens symboliques
        if not run_command(f"ln -s {tmp_static_path} {static_path}", elevated=True):
            raise Exception("Failed to create deploy symlink")
        # Créer le lien symbolique staging seulement s'il n'existe pas déjà
        if not os.path.exists(staging_path):
            if not run_command(f"ln -s {tmp_staging_path} {staging_path}", elevated=True):
                raise Exception("Failed to create staging symlink")
        
        # S'assurer que les liens symboliques ont les bonnes permissions
        if not run_command(f"chown -h www-data:www-data {static_path}", elevated=True):
            raise Exception("Failed to set ownership on deploy symlink")
        if not run_command(f"chown -h www-data:www-data {staging_path}", elevated=True):
            raise Exception("Failed to set ownership on staging symlink")

        # Force Elementor data update
        try:
            socketio.emit("console", "Mise à jour de la base de données Elementor.")
            run_command(f"wp elementor update db --path={wp_path}")
        except Exception as e:
            if "is not a registered wp command" in str(e):
                socketio.emit("console", "Elementor command not found, skipping Elementor data update.")
            else:
                raise Exception("Failed to update Elementor data")

        # Try to activate Staatic plugin
        try:
            socketio.emit("console", "Activation du plugin Staatic.")
            result = run_command(f"wp plugin activate staatic --path={wp_path}", return_output=True)
            socketio.emit("console", f"Activation de Staatic: {result}")
        except Exception:
            socketio.emit("console", "Erreur lors de l'activation des plugins, mais on continue.")

        # Run Staatic export
        socketio.emit("console", "Exécution de l'exportation Staatic.")
        result = run_command(f"wp staatic publish --force --path={wp_path}", return_output=True)  # Store result
        if "Success: Publication finished" in result:
            socketio.emit("console", "Exportation réussie.")
            # Déplacement des fichiers vers le répertoire de destination.
            socketio.emit("console", "Déplacement des fichiers vers le répertoire de destination.")

            # Ensure the destination path exists and set permissions
            if not os.path.exists(destination_path):
                socketio.emit("console", "Création du répertoire de destination.")
                if not run_command(f"mkdir -p {destination_path}", elevated=True):
                    raise Exception("Failed to create destination path")

            # Move the content from static_path to destination_path
            if os.path.exists(static_path) and os.listdir(static_path):
                # Remove existing content in destination path if it exists
                if os.path.exists(destination_path):
                    if not run_command(f"rm -rf {destination_path}/*", elevated=True):
                        raise Exception("Failed to clean destination path")
                
                # Update canonical links
                socketio.emit("console", "Mise à jour des liens canoniques.")
                update_canonical_links(static_path, domain_name)

                # Move all content from static_path to destination_path
                if not run_command(f"mv {static_path}/* {destination_path}/", elevated=True):
                    raise Exception("Failed to move files to destination path")
                
                # Set ownership of the destination path to www-data
                if not run_command(f"chown -R www-data:www-data {destination_path}", elevated=True):
                    raise Exception("Failed to change ownership of destination path to www-data")
                
                socketio.emit("success", f"Déploiement réussi pour {domain_name}.")
                success = True
            else:
                socketio.emit("error", f"Aucun fichier trouvé dans {static_path}.")
                success = False
        else:
            socketio.emit("error", f"Erreur lors de l'exportation Staatic: {result}")
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
    delete_old_deployment_logs()  # Call the function to delete old logs

def delete_old_deployment_logs():
    log_path = "data/deployments.json"
    if os.path.exists(log_path):
        with open(log_path, "r") as log_file:
            logs = json.load(log_file)
        one_month_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        logs = [log for log in logs if datetime.datetime.fromtimestamp(log["timestamp"]) > one_month_ago]
        with open(log_path, "w") as log_file:
            json.dump(logs, log_file, indent=4)
        run_command("chown www-data:www-data data/deployments.json", elevated=True)

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
        response = requests.get(f"https://{domain}/")
        response_bo = requests.get(f"https://bo.{domain}/")
        return response.status_code == 200 and response_bo.status_code == 200
    except Exception as e:
        socketio.emit("console", f"Erreur lors de la vérification du statut pour le domaine : {domain}, Erreur : {str(e)}")
        return False

def update_sites_data(indexed=False, specific_domain=None):
    try:
        existing_data = load_sites_data()
        existing_domains = {site['domain']: site for site in existing_data.get('sites', [])}
        
        # Si un domaine spécifique est fourni, ne traiter que celui-là
        domains = [specific_domain] if specific_domain else [
            domain for domain in os.listdir('/var/www/')
            if os.path.isdir(os.path.join('/var/www/', domain))
            and not domain.startswith('.')
            and not domain.endswith('-static')
        ]

        sites = []
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

        sites_data = {
            "sites": list(existing_domains.values()),
            "last_update": datetime.datetime.now().strftime("%d/%m/%Y - %Hh%M")
        }
        save_sites_data(sites_data)
    except Exception as e:
        socketio.emit("error", f"Erreur lors de la mise à jour des données des sites: {str(e)}")

def verify_paths(domain_name):
    try:
        base_path = os.path.realpath("/var/www")
        wp_path = os.path.join(base_path, domain_name)

        # Verify paths exist and have correct permissions
        paths_to_check = [base_path, wp_path]
        for path in paths_to_check:
            if not os.path.exists(path):
                raise Exception(f"Path does not exist: {path}")
            
            # Check if www-data has access
            if not run_command(f"test -r {path} && test -w {path}", elevated=True):
                raise Exception(f"Insufficient permissions on path: {path}")

        return True
    except Exception as e:
        socketio.emit("error", f"Path verification failed: {str(e)}")
        return False

def update_canonical_links(static_path, domain_name):
    """Update canonical links in all HTML files to include the full domain."""
    try:
        run_command(f'find {static_path} -type f -name "*.html" -exec sed -i "s|<link rel=\\"canonical\\" href=\\"/|<link rel=\\"canonical\\" href=\\"https://{domain_name}/|g" {{}} \\;', elevated=True)
    except Exception as e:
        socketio.emit("console", f"Erreur lors de la mise à jour des liens canoniques: {str(e)}")
