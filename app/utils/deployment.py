import os
import json
import datetime
import requests
from app import socketio
from .system import run_command
from .wordpress import get_published_articles
from .settings import save_sites_data

def deploy_static(domain_name):
    try:
        wp_path = f"/var/www/{domain_name}"
        static_path = f"{wp_path}/wp-content/uploads/simply-static/temp-files/"

        if os.path.exists(static_path):
            if not run_command(f"rm -rf {static_path}", elevated=True):
                raise Exception("Failed to remove static path")

        # Force Elementor data update
        if not run_command(f"wp elementor update db --path={wp_path}"):
            raise Exception("Failed to update Elementor data")

        # Run Simply Static export
        if not run_command(f"wp simply-static run --path={wp_path}"):
            raise Exception("Failed to run Simply Static export")

        # Check if the export was successful
        result = run_command(f"wp simply-static run --path={wp_path}", return_output=True)
        if "Success: Export Completed" in result:
            # Move the first zip file in static path to the destination and copy content if folder exists
            zip_files = [f for f in os.listdir(static_path) if f.endswith(".zip")]
            if zip_files:
                first_zip = zip_files[0]
                folder_name = first_zip[:-4]  # Remove the .zip extension to get the folder name
                folder_path = os.path.join(static_path, folder_name)
                destination_path = f"/opt/websites/{domain_name}"

                # Ensure the destination path exists and set permissions
                if not os.path.exists(destination_path):
                    if not run_command(f"mkdir -p {destination_path}", elevated=True):
                        raise Exception("Failed to create destination path")
                    if not run_command(f"chown -R www-data:www-data {destination_path}", elevated=True):
                        raise Exception("Failed to change ownership of destination path")

                # Check if the folder with the same name as the zip file exists
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    if not run_command(f"cp -r {folder_path}/* {destination_path}", elevated=True):
                        raise Exception("Failed to copy folder contents to destination path")
                else:
                    if not run_command(f"unzip {os.path.join(static_path, first_zip)} -d {destination_path}"):
                        raise Exception("Failed to unzip file to destination path")

                # Create Readme.md with deployment details
                readme_content = f"# Deployment Info\n\nDomain: {domain_name}\n\nDate: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                with open(os.path.join(destination_path, "Readme.md"), "w") as readme_file:
                    readme_file.write(readme_content)

                # Add, commit, and push changes to the git repository, forcing the push even if the tree is clean or up-to-date
                if not run_command(f"cd {destination_path} && git add . && git commit -m 'Deploy static site' && git push --force"):
                    raise Exception("Failed to push changes to git repository")

                # Clear the static path
                if not run_command(f"rm -rf {static_path}"):
                    raise Exception("Failed to clear static path")
            else:
                socketio.emit("error", f"Aucun fichier ZIP trouvé dans {static_path}.")
                return False
        else:
            socketio.emit("error", f"Erreur lors de l'exportation Simply Static: {result}")
            return False
        return True
    except Exception as e:
        socketio.emit(
            "error", f"Erreur lors du déploiement statique pour {domain_name}: {str(e)}"
        )
        return False

def log_deployment(domain_name, success, duration):
    log_entry = {
        "domain": domain_name,
        "success": success,
        "time": datetime.datetime.now().isoformat(),
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

def format_deployment_log(deployment):
    deployment["time"] = datetime.datetime.fromisoformat(deployment["time"]).strftime(
        "%d/%m/%Y %H:%M:%S"
    )
    deployment["duration"] = f"{deployment['duration']:.2f}"
    return deployment

def get_indexed_articles(domain_name):
    api_key = "33cef647-1f76-4604-927d-e7f0d5b93205"
    return 0
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
        if os.path.isdir(os.path.join("/var/www/", domain)) and not domain.startswith(".")
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
            "status": status
        }

    sites_data["sites"] = list(existing_domains.values())
    sites_data['last_update'] = datetime.datetime.now().strftime("%d/%m/%Y - %Hh%M")
    save_sites_data(sites_data)