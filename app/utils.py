from internetbs import Domain, DNS
import json, os
import subprocess
import random
import string
import requests
import datetime
from functools import lru_cache
from app import socketio
from werkzeug.security import check_password_hash, generate_password_hash


def run_command(command, elevated=False):
    if elevated:
        command = f"sudo -s {command}"
    try:
        # Use subprocess.run with timeout and capture_output for better control
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True, timeout=300
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        socketio.emit("error", f"Erreur: {e.stderr}")
    except subprocess.TimeoutExpired:
        socketio.emit(
            "error", f"Timeout: La commande a pris trop de temps à s'exécuter"
        )
    except Exception as e:
        socketio.emit("error", f"Erreur inattendue: {str(e)}")
    return None


def format_deployment_log(deployment):
    deployment["time"] = datetime.datetime.fromisoformat(deployment["time"]).strftime(
        "%d/%m/%Y %H:%M:%S"
    )
    deployment["duration"] = f"{deployment['duration']:.2f}"
    return deployment


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


@lru_cache(maxsize=32)
def load_settings():
    from app import socketio
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
    from app import socketio  # Importer socketio ici pour éviter l'importation circulaire
    run_command("chown www-data:www-data data", elevated=True)
    config_path = "data/config.json"
    try:
        with open(config_path, "w") as config_file:
            json.dump(settings, config_file, indent=4)
        run_command("chown www-data:www-data data/config.json", elevated=True)
    except Exception as e:
        socketio.emit("error", f"Erreur lors de la sauvegarde des paramètres: {str(e)}")


# Load settings
settings = load_settings()
api_key = settings["internetbs_token"]
password = settings["internetbs_password"]
test_mode = settings["test_mode"]

domain = Domain(api_key, password, test_mode)
dns = DNS(api_key, password, test_mode)


def publish_article(site, title, content, image_path=None):
    wp_path = f"/var/www/{site}"
    # Escape single quotes in title and content
    title = title.replace("'", "\\'")
    content = content.replace("'", "\\'")
    
    # Create the post
    create_command = f"wp post create --post_type=post --post_title='{title}' --post_content='{content}' --post_status=publish --porcelain --path={wp_path}"
    post_id = run_command(create_command)
    
    if post_id:
        socketio.emit("message", f'Article "{title}" publié sur {site}.')
        
        if image_path:
            # Import the image and set it as featured image
            import_command = f"wp media import '{image_path}' --porcelain --path={wp_path}"
            attachment_id = run_command(import_command)
            
            if attachment_id:
                set_featured_command = f"wp post meta add {post_id} _thumbnail_id {attachment_id} --path={wp_path}"
                if run_command(set_featured_command):
                    socketio.emit("message", f'Image à la une ajoutée pour l\'article "{title}" sur {site}.')
                else:
                    socketio.emit("error", f'Erreur lors de la définition de l\'image à la une pour l\'article "{title}" sur {site}.')
            else:
                socketio.emit("error", f'Erreur lors de l\'import de l\'image pour l\'article "{title}" sur {site}.')
    else:
        socketio.emit("error", f'Erreur lors de la publication de l\'article "{title}" sur {site}.')


def is_domain_owned(domain_name):
    socketio.emit(
        "message", f"Vérification de la possession du domaine {domain_name}..."
    )
    domains = domain.list_domains()
    for d in domains:
        if d.domain_name == domain_name:
            socketio.emit("message", f"Domaine {domain_name} est déjà possédé.")
            return True
    return False


def is_domain_available(domain_name):
    available = domain.check_availability(domain_name)
    socketio.emit(
        "message",
        (
            f"Domaine {domain_name} est disponible."
            if available
            else f"Domaine {domain_name} n'est pas disponible."
        ),
    )
    return available


def purchase_domain(domain_name, contacts):
    try:
        result = domain.create_domain(domain_name, contacts)
        socketio.emit("message", f"Domaine {domain_name} a été acheté.")
        return result
    except Exception as e:
        socketio.emit(
            "error", f"Erreur lors de l'achat du domaine {domain_name}: {str(e)}"
        )
        return None


def configure_dns(domain_name):
    dns_records = [
        {"name": f"bo.{domain_name}", "type": "A", "value": "51.210.255.66"},
        {
            "name": f"bo.{domain_name}",
            "type": "AAAA",
            "value": "2001:41d0:304:200::5ec6",
        },
        {"name": f"{domain_name}", "type": "A", "value": "185.199.108.153"},
        {"name": f"{domain_name}", "type": "AAAA", "value": "2606:50c0:8000::153"},
    ]

    for record in dns_records:
        try:
            dns.remove_record(record["name"], record["type"])
        except Exception:
            pass
        try:
            result = dns.add_record(record["name"], record["type"], record["value"])
            socketio.emit(
                "message",
                f'Enregistrement DNS {record["type"]} pour {record["name"]} configuré à {record["value"]}.',
            )
        except Exception as e:
            socketio.emit(
                "error",
                f'Erreur lors de la configuration DNS {record["type"]} pour {record["name"]}: {str(e)}',
            )
            return None
    return True


def create_nginx_config(domain_name, force=False):
    try:
        config_path = f"/etc/nginx/sites-available/bo.{domain_name}"
        if os.path.exists(config_path) and not force:
            socketio.emit(
                "confirm",
                {
                    "message": f"Configuration Nginx pour bo.{domain_name} existe déjà. Voulez-vous continuer ?",
                    "action": "create_nginx_config",
                },
            )
            return False

        # Create a temporary file for the Nginx config
        temp_config_path = f"/tmp/nginx_config_{domain_name}.conf"
        with open(temp_config_path, "w") as temp_config_file:
            temp_config_file.write(
                f"""
            server {{
                listen 80;
                server_name bo.{domain_name};

                root /var/www/{domain_name};
                index index.php index.html index.htm;

                location / {{
                    try_files $uri $uri/ /index.php?$args;
                }}

                location ~ \.php$ {{
                    include snippets/fastcgi-php.conf;
                    fastcgi_pass unix:/var/run/php/php8.2-fpm.sock;
                }}

                location ~ /\.ht {{
                    deny all;
                }}
            }}
            """
            )

        # Move the temporary file to the Nginx config directory with elevated privileges
        run_command(f"mv {temp_config_path} {config_path}", elevated=True)

        if os.path.exists(f"/etc/nginx/sites-enabled/bo.{domain_name}"):
            run_command(f"rm /etc/nginx/sites-enabled/bo.{domain_name}", elevated=True)

        run_command(
            f"ln -s {config_path} /etc/nginx/sites-enabled/bo.{domain_name}",
            elevated=True,
        )
        run_command("systemctl reload nginx", elevated=True)
        socketio.emit("message", f"Configuration Nginx pour bo.{domain_name} créée.")

        return True
    except Exception as e:
        socketio.emit(
            "error",
            f"Erreur lors de la création de la configuration Nginx pour bo.{domain_name}: {str(e)}",
        )
        return False


def setup_ssl(domain_name):
    try:
        settings = load_settings()
        registrant_email = settings["registrant"]["email"]
        # Install Certbot and obtain SSL certificate
        run_command(
            f"certbot --nginx  -d bo.{domain_name} --non-interactive --agree-tos -m {registrant_email}",
            elevated=True,
        )
        socketio.emit("message", f"SSL configuré pour bo.{domain_name}.")
        return True
    except Exception as e:
        socketio.emit(
            "error",
            f"Erreur lors de la configuration SSL pour bo.{domain_name}: {str(e)}",
        )
        return False


def install_wordpress(domain_name, force=False):
    try:
        settings = load_settings()
        wp_path = f"/var/www/{domain_name}"
        if os.path.exists(wp_path):
            if not force:
                socketio.emit(
                    "confirm",
                    {
                        "message": f"WordPress est déjà installé pour {domain_name}. Voulez-vous continuer ?",
                        "action": "install_wordpress",
                    },
                )
                return False
            else:
                run_command(f"rm -rf {wp_path}", elevated=True)
        else:
            run_command(f"mkdir -p {wp_path}", elevated=True)
            run_command(f"chown www-data:www-data {wp_path}", elevated=True)

        # Generate random names for the database and user
        unique_db_name = "".join(
            random.choices(string.ascii_letters + string.digits, k=16)
        )
        unique_db_user = "".join(
            random.choices(string.ascii_letters + string.digits, k=16)
        )
        unique_db_password = "".join(
            random.choices(string.ascii_letters + string.digits, k=16)
        )
        registrant_email = settings["registrant"]["email"]

        # Download WordPress
        run_command(f"wp core download --path={wp_path} --locale=fr_FR")

        # Create the database
        run_command(
            f"mysql -u root -e 'CREATE DATABASE {unique_db_name};'", elevated=True
        )

        # Create a unique user for WordPress
        run_command(
            f"mysql -u root -e 'CREATE USER wp_{unique_db_user}@localhost IDENTIFIED BY \"{unique_db_password}\";'",
            elevated=True,
        )
        run_command(
            f"mysql -u root -e 'GRANT ALL PRIVILEGES ON {unique_db_name}.* TO wp_{unique_db_user}@localhost;'",
            elevated=True,
        )
        run_command(f"mysql -u root -e 'FLUSH PRIVILEGES;'", elevated=True)

        socketio.emit(
            "message",
            f"Base de données WordPress {unique_db_name} créée avec le mot de passe {unique_db_password} pour wp_{unique_db_user}.",
        )

        # Create wp-config.php
        run_command(
            f"wp config create --path={wp_path} --dbname={unique_db_name} --dbuser=wp_{unique_db_user} --dbpass={unique_db_password} --dbhost=localhost --skip-check"
        )

        # Install WordPress
        run_command(
            f"wp core install --path={wp_path} --url=https://bo.{domain_name} --title='{domain_name}' --admin_user=admin --admin_password={unique_db_password} --admin_email={registrant_email} --locale=fr_FR"
        )

        # Update wp cli
        run_command(f"wp cli update --path={wp_path}", elevated=True)

        # Install WP Login
        run_command(
            f"wp package install aaemnnosttv/wp-cli-login-command --path={wp_path} --url=https://bo.{domain_name}"
        )

        # Install Companion plugin
        run_command(
            f"wp login install --activate --path={wp_path} --url=https://bo.{domain_name}"
        )

        # Install and activate Simply Static
        run_command(
            f"wp plugin install simply-static --activate --path={wp_path} --url=https://bo.{domain_name}"
        )

        # Install and activate Simply Static Pro
        run_command(
            f"wp plugin install ./vendor/ssp.zip --activate --path={wp_path} --url=https://bo.{domain_name}"
        )

        socketio.emit("message", f"WordPress installé pour {domain_name}.")
        return True
    except Exception as e:
        socketio.emit(
            "error",
            f"Erreur lors de l'installation de WordPress pour {domain_name}: {str(e)}",
        )
        return False


def generate_wp_login_link(domain_name):
    wp_path = f"/var/www/{domain_name}"
    try:
        command = (
            f"wp login create admin --path={wp_path} --url=https://bo.{domain_name}"
        )
        result = run_command(command)
        if result:
            lines = result.strip().split("\n")
            login_link = lines[2].strip()
            return login_link
    except Exception as e:
        socketio.emit(
            "error",
            f"Erreur lors de la génération du lien de connexion automatique pour {domain_name}: {str(e)}",
        )
    return None


def get_published_articles(domain_name):
    wp_path = f"/var/www/{domain_name}"
    command = f"wp post list --post_type=post --post_status=publish --format=count --path={wp_path}"
    result = run_command(command)
    return int(result.strip()) if result else 0


def get_indexed_articles(domain_name):
    api_key = "33cef647-1f76-4604-927d-e7f0d5b93205"
    url = f"https://api.spaceserp.com/google/search?apiKey={api_key}&q=site%3A{domain_name}&location=Lyon%2CAuvergne-Rhone-Alpes%2CFrance&domain=google.fr&gl=fr&hl=fr&resultFormat=json&resultBlocks=total_results_count"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("total_results_count", 0)
    return 0


def initialize_git_repo(domain_name):
    repo_path = f"/opt/websites/{domain_name}"
    try:
        if os.path.exists(repo_path):
            run_command(f"rm -rf {repo_path}", elevated=True)
        os.makedirs(repo_path)

        # Initialize a local git repository
        run_command(f"git init {repo_path}")

        # Create a CNAME file with the domain name
        cname_path = os.path.join(repo_path, "CNAME")
        with open(cname_path, "w") as cname_file:
            cname_file.write(domain_name)

        # Add and commit the CNAME file
        run_command(
            f"cd {repo_path} && git add CNAME && git commit -m 'Add CNAME file'"
        )

        github_token = settings["github_token"]
        github_username = settings["github_username"]

        # Check if the repository already exists and delete it if it does
        response = requests.get(
            f"https://api.github.com/repos/{github_username}/{domain_name}",
            headers={
                "Authorization": f"token {github_token}",
                "Content-Type": "application/json",
            },
        )
        if response.status_code == 200:
            run_command(
                f"curl -X DELETE -H 'Authorization: token {github_token}' https://api.github.com/repos/{github_username}/{domain_name}"
            )

        # Create a GitHub repository
        run_command(
            f"curl -X POST -H 'Authorization: token {github_token}' -H 'Content-Type: application/json' -d '{{ \"name\": \"{domain_name}\" }}' https://api.github.com/user/repos"
        )

        # Add the remote origin and push the initial commit
        run_command(
            f"cd {repo_path} && git remote add origin https://{github_token}@github.com/{github_username}/{domain_name}.git"
        )
        run_command(f"cd {repo_path} && git push -u origin master")

        # Enable GitHub Pages with SSL
        pages_data = {"source": {"branch": "master", "path": "/"}}
        run_command(
            f"curl -X POST -H 'Authorization: token {github_token}' -H 'Content-Type: application/json' -d '{json.dumps(pages_data)}' https://api.github.com/repos/{github_username}/{domain_name}/pages"
        )

        # Enforce HTTPS
        run_command(
            f"curl -X PATCH -H 'Authorization: token {github_token}' -H 'Content-Type: application/json' -d '{{ \"enforce_https\": true }}' https://api.github.com/repos/{github_username}/{domain_name}"
        )

        socketio.emit(
            "message",
            f"Dépôt GitHub {domain_name} créé, initialisé avec un fichier CNAME, et GitHub Pages activé avec SSL.",
        )
        return True
    except Exception as e:
        socketio.emit(
            "error",
            f"Erreur lors de l'initialisation du dépôt Git pour {domain_name}: {str(e)}",
        )
        return False


def deploy_static(domain_name):
    try:
        wp_path = f"/var/www/{domain_name}"
        static_path = f"{wp_path}/wp-content/uploads/simply-static/temp-files/"

        if os.path.exists(static_path):
            run_command(f"rm -rf {static_path}", elevated=True)

        # Run Simply Static export
        result = run_command(f"wp simply-static run --path={wp_path}")

        # Check if the export was successful
        if "Success: Export Completed" in result:
            # Move the first zip file in static path to the destination and copy content if folder exists
            zip_files = [f for f in os.listdir(static_path) if f.endswith(".zip")]
            if zip_files:
                first_zip = zip_files[0]
                folder_name = first_zip[
                    :-4
                ]  # Remove the .zip extension to get the folder name
                folder_path = os.path.join(static_path, folder_name)
                destination_path = f"/opt/websites/{domain_name}"

                # Ensure the destination path exists and set permissions
                if not os.path.exists(destination_path):
                    run_command(f"mkdir -p {destination_path}", elevated=True)
                    run_command(
                        f"chown -R www-data:www-data {destination_path}", elevated=True
                    )

                # Check if the folder with the same name as the zip file exists
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    run_command(
                        f"cp -r {folder_path}/* {destination_path}", elevated=True
                    )
                else:
                    run_command(
                        f"unzip {os.path.join(static_path, first_zip)} -d {destination_path}"
                    )

                # Add, commit, and push changes to the git repository
                run_command(
                    f"cd {destination_path} && git add . && git commit -m 'Deploy static site' && git push"
                )

                # Clear the static path
                run_command(f"rm -rf {static_path}")
            else:
                socketio.emit("error", f"Aucun fichier ZIP trouvé dans {static_path}.")
                return False
        else:
            socketio.emit("error", "Erreur lors de l'exportation Simply Static.")
            return False
        return True
    except Exception as e:
        socketio.emit(
            "error", f"Erreur lors du déploiement statique pour {domain_name}: {str(e)}"
        )
        return False


def fetch_site_data():
    sites = []
    for domain in os.listdir("/var/www/"):
        if os.path.isdir(os.path.join("/var/www/", domain)) and not domain.startswith(
            "."
        ):
            published_articles = get_published_articles(domain)
            indexed_articles = get_indexed_articles(domain)
            indexed_percentage = (
                (indexed_articles / published_articles * 100)
                if published_articles > 0
                else 0
            )
            site_info = {
                "domain": domain,
                "status": "online",
                "published_articles": published_articles,
                "indexed_articles": indexed_articles,
                "indexed_percentage": indexed_percentage,
            }
            sites.append(site_info)
    return sites


def save_site_data():
    data = {
        "sites": fetch_site_data(),
        "last_update": datetime.datetime.now().strftime("%d/%m/%Y - %Hh%M"),
    }
    run_command("chown www-data:www-data data", elevated=True)
    with open("data/data.json", "w") as f:
        json.dump(data, f, indent=4)
    run_command("chown www-data:www-data data/data.json", elevated=True)


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
