import os
import json
import datetime
import requests
from app import socketio
from .system import run_command
from .wordpress import get_published_articles
from .settings import load_sites_data, save_sites_data

class DeploymentLogger:
    def __init__(self, domain_name):
        self.domain_name = domain_name
        self.logs = []

    def log_message(self, message):
        """Log a message both to console and to the logs list."""
        formatted_message = f"[{self.domain_name}] {message}"
        self.logs.append({"time": datetime.datetime.now().strftime('%H:%M:%S'), "message": formatted_message})
        socketio.emit("console", formatted_message)

def deploy_static(domain_name):
    logger = DeploymentLogger(domain_name)
    start_time = datetime.datetime.now()
    try:
        # Verify paths before proceeding
        if not verify_paths(domain_name, logger):
            raise Exception("Path verification failed")
            
        # Resolve the real paths
        base_path = os.path.realpath("/var/www")
        wp_path = os.path.join(base_path, domain_name)
        staatic_base = os.path.join(wp_path, "wp-content/uploads/staatic")
        static_path = os.path.join(staatic_base, "deploy")
        staging_path = os.path.join(staatic_base, "staging")
        destination_path = os.path.join("/var/www/static", domain_name)
        tmp_static_path = os.path.join("/mnt/disk2/tmpstatic", domain_name)
        tmp_staging_path = os.path.join("/mnt/disk2/staging", domain_name)
        tmp_dir = "/mnt/disk2/tmp"

        logger.log_message("Début du déploiement.")

        # Créer et configurer les répertoires temporaires principaux si nécessaire
        for tmp_path in ["/mnt/disk2/tmpstatic", "/mnt/disk2/staging", tmp_dir]:
            if not os.path.exists(tmp_path):
                logger.log_message(f"Création du répertoire temporaire {tmp_path}")
                if not run_command(f"mkdir -p {tmp_path}", elevated=True):
                    raise Exception(f"Failed to create temporary directory: {tmp_path}")
                if not run_command(f"chown www-data:www-data {tmp_path}", elevated=True):
                    raise Exception(f"Failed to set ownership on temporary directory: {tmp_path}")
                if not run_command(f"chmod 755 {tmp_path}", elevated=True):
                    raise Exception(f"Failed to set permissions on temporary directory: {tmp_path}")

        # S'assurer que le répertoire parent de Staatic existe
        logger.log_message("Configuration des répertoires Staatic")
        if not run_command(f"mkdir -p {staatic_base}", elevated=True):
            raise Exception("Failed to create Staatic base directory")
        if not run_command(f"chown www-data:www-data {staatic_base}", elevated=True):
            raise Exception("Failed to set ownership on Staatic base directory")
        if not run_command(f"chmod 755 {staatic_base}", elevated=True):
            raise Exception("Failed to set permissions on Staatic base directory")

        # Supprimer uniquement l'ancien lien symbolique deploy s'il existe
        if os.path.exists(static_path):
            logger.log_message("Suppression de l'ancien lien symbolique: deploy")
            if not run_command(f"rm -rf {static_path}", elevated=True):
                raise Exception("Failed to remove old deploy symlink")

        # Ne pas supprimer le lien symbolique staging s'il existe déjà
        if os.path.exists(staging_path) and not os.path.islink(staging_path):
            logger.log_message("Configuration initiale du staging")
            if not run_command(f"rm -rf {staging_path}", elevated=True):
                raise Exception("Failed to remove old staging directory")

        # Supprimer l'ancien répertoire temporaire deploy s'il existe
        if os.path.exists(tmp_static_path):
            logger.log_message("Nettoyage de l'ancien répertoire temporaire")
            if not run_command(f"rm -rf {tmp_static_path}", elevated=True):
                raise Exception("Failed to remove old temporary deploy directory")

        # Créer les répertoires temporaires avec les bonnes permissions
        for tmp_path in [tmp_static_path, tmp_staging_path]:
            if not os.path.exists(tmp_path):
                logger.log_message(f"Création du répertoire temporaire: {os.path.basename(tmp_path)}")
                if not run_command(f"mkdir -p {tmp_path}", elevated=True):
                    raise Exception(f"Failed to create temporary directory: {tmp_path}")
                if not run_command(f"chown www-data:www-data {tmp_path}", elevated=True):
                    raise Exception(f"Failed to set ownership on: {tmp_path}")
                if not run_command(f"chmod 755 {tmp_path}", elevated=True):
                    raise Exception(f"Failed to set permissions on: {tmp_path}")

        # Créer les liens symboliques
        logger.log_message("Création des liens symboliques")
        if not run_command(f"ln -s {tmp_static_path} {static_path}", elevated=True):
            raise Exception("Failed to create deploy symlink")
        if not os.path.exists(staging_path):
            if not run_command(f"ln -s {tmp_staging_path} {staging_path}", elevated=True):
                raise Exception("Failed to create staging symlink")

        # Force Elementor data update
        try:
            result = run_command(f"wp elementor update db --path={wp_path}", return_output=True)
            if "is not a registered wp command" not in result:
                logger.log_message("Mise à jour de la base de données Elementor")
            else:
                logger.log_message(f"Erreur: {result}")
        except Exception as e:
            logger.log_message(f"Erreur: {str(e)}")

        # Try to activate Staatic plugin
        try:
            logger.log_message("Activation du plugin Staatic")
            result = run_command(f"wp plugin activate staatic --path={wp_path}", return_output=True)
            logger.log_message(f"Activation de Staatic: {result}")
        except Exception as e:
            logger.log_message(f"Erreur lors de l'activation des plugins: {str(e)}")

        # Run Staatic export
        logger.log_message("Exécution de l'exportation Staatic")
        result = run_command(f"wp staatic publish --force --path={wp_path}", return_output=True)
        if "Success: Publication finished" in result:
            logger.log_message("Exportation réussie")
            
            # Vérification des fichiers avant la copie
            files_ok, files_info = verify_static_files(static_path, domain_name, logger)
            if not files_ok:
                logger.log_message(f"Erreur lors de la vérification des fichiers: {files_info}")
                success = False
            else:
                logger.log_message(f"{len(files_info)} fichiers prêts à être déployés")
                logger.log_message("Déplacement des fichiers vers le répertoire de destination")

                try:
                    # Ensure the destination path exists and is not a symlink
                    if os.path.islink(destination_path):
                        if not run_command(f"rm -f {destination_path}", elevated=True):
                            raise Exception("Failed to remove old destination symlink")
                    
                    if not os.path.exists(destination_path):
                        if not run_command(f"mkdir -p {destination_path}", elevated=True):
                            raise Exception("Failed to create destination path")

                    # Copier d'abord vers un répertoire temporaire
                    temp_dest = f"/mnt/disk2/tmp/{domain_name}_temp"
                    if not run_command(f"rm -rf {temp_dest}", elevated=True):
                        raise Exception("Failed to clean temporary directory")
                    if not run_command(f"mkdir -p {temp_dest}", elevated=True):
                        raise Exception("Failed to create temporary directory")
                    
                    # Copier les fichiers vers le répertoire temporaire
                    result = run_command(f"cp -rf {static_path}/* {temp_dest}/", elevated=True, return_output=True)
                    if result:
                        logger.log_message(f"Résultat de la copie: {result}")
                    
                    # Déplacer les fichiers vers la destination finale
                    if not run_command(f"rm -rf {destination_path}/*", elevated=True):
                        raise Exception("Failed to clean destination directory")
                    result = run_command(f"mv {temp_dest}/* {destination_path}/", elevated=True, return_output=True)
                    if result:
                        logger.log_message(f"Résultat du déplacement: {result}")
                    
                    if not run_command(f"rm -rf {temp_dest}", elevated=True):
                        raise Exception("Failed to clean temporary directory")
                    
                    # Nettoyer le répertoire source
                    if not run_command(f"rm -rf {static_path}/*", elevated=True):
                        raise Exception("Failed to clean static path")
                    
                    # Update canonical links
                    logger.log_message("Mise à jour des liens canoniques dans destination_path")
                    try:
                        result = run_command(f'find {destination_path} -type f -name "*.html" -exec sed -i "s|<link rel=\\"canonical\\" href=\\"/|<link rel=\\"canonical\\" href=\\"https://{domain_name}/|g" {{}} \\;', elevated=True, return_output=True)
                        if result:
                            logger.log_message(f"Résultat de la mise à jour des liens: {result}")
                    except Exception as e:
                        logger.log_message(f"Erreur lors de la mise à jour des liens canoniques: {str(e)}")

                    if not run_command(f"chown -R www-data:www-data {destination_path}", elevated=True):
                        raise Exception("Failed to change ownership of destination path to www-data")
                    
                    logger.log_message("Déploiement réussi")
                    success = True
                except Exception as e:
                    logger.log_message(f"Erreur lors du déploiement: {str(e)}")
                    success = False
        else:
            logger.log_message(f"Erreur lors de l'exportation Staatic: {result}")
            success = False

        duration = (datetime.datetime.now() - start_time).total_seconds()
        log_deployment(domain_name, success, duration, logger.logs)
        return success
    except Exception as e:
        error_message = f"Erreur lors du déploiement statique: {str(e)}"
        logger.log_message(error_message)
        log_deployment(domain_name, False, 0, logger.logs)
        return False

def log_deployment(domain_name, success, duration, console_logs=None):
    log_entry = {
        "domain": domain_name,
        "success": success,
        "timestamp": int(datetime.datetime.now().timestamp()),
        "time": datetime.datetime.now().strftime('%d/%m/%Y - %Hh%M'),
        "duration": round(duration, 2),
        "console_logs": console_logs or []
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
    )
    delete_old_deployment_logs()

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
        if not isinstance(existing_data, dict):
            existing_data = {"sites": [], "last_update": ""}
            
        existing_domains = {site['domain']: site for site in existing_data.get('sites', [])}
        
        # Si un domaine spécifique est fourni, ne traiter que celui-là
        domains = [specific_domain] if specific_domain else [
            domain for domain in os.listdir('/var/www/')
            if os.path.isdir(os.path.join('/var/www/', domain))
            and not domain.startswith('.')
            and not domain.endswith('-static')
        ]
        
        for domain in domains:
            try:
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
            except Exception as e:
                socketio.emit("error", f"Erreur lors de la mise à jour du domaine {domain}: {str(e)}")
                continue

        sites_data = {
            "sites": list(existing_domains.values()),
            "last_update": datetime.datetime.now().strftime("%d/%m/%Y - %Hh%M")
        }
        save_sites_data(sites_data)
    except Exception as e:
        socketio.emit("error", f"Erreur lors de la mise à jour des données des sites: {str(e)}")

def verify_paths(domain_name, logger):
    try:
        base_path = os.path.realpath("/var/www")
        wp_path = os.path.join(base_path, domain_name)

        paths_to_check = [base_path, wp_path]
        for path in paths_to_check:
            if not os.path.exists(path):
                raise Exception(f"Path does not exist: {path}")
            
            if not run_command(f"test -r {path} && test -w {path}", elevated=True):
                raise Exception(f"Insufficient permissions on path: {path}")

        return True
    except Exception as e:
        logger.log_message(f"Path verification failed: {str(e)}")
        return False

def update_canonical_links(static_path, domain_name, logger):
    try:
        result = run_command(f'find {static_path} -type f -name "*.html" -exec sed -i "s|<link rel=\\"canonical\\" href=\\"/|<link rel=\\"canonical\\" href=\\"https://{domain_name}/|g" {{}} \\;', elevated=True, return_output=True)
        if result:
            logger.log_message(f"Résultat de la mise à jour des liens: {result}")
    except Exception as e:
        logger.log_message(f"Erreur lors de la mise à jour des liens canoniques: {str(e)}")

def verify_static_files(static_path, domain_name, logger):
    try:
        if not os.path.exists(static_path):
            raise Exception(f"Le répertoire source n'existe pas: {static_path}")
        
        if not os.path.isdir(static_path):
            raise Exception(f"Le chemin source n'est pas un répertoire: {static_path}")
            
        files = os.listdir(static_path)
        if not files:
            raise Exception("Aucun fichier trouvé dans le répertoire source")
            
        html_files = [f for f in files if f.endswith('.html')]
        if not html_files:
            raise Exception("Aucun fichier HTML trouvé dans l'export")
            
        return True, files
    except Exception as e:
        return False, str(e)
