import os
import random
import string
from app import socketio
from .system import run_command
from .settings import load_settings
import shlex

def create_nginx_config(domain_name):
    try:
        # Backend configuration (bo.)
        bo_config_path = f"/etc/nginx/sites-available/bo.{domain_name}"
        bo_temp_config_path = f"/tmp/nginx_config_bo_{domain_name}.conf"
        
        with open(bo_temp_config_path, "w") as temp_config_file:
            temp_config_file.write(
                f"""
server {{
    listen 80;
    server_name bo.{domain_name};

    root /var/www/{domain_name};
    index index.php index.html index.htm;

    access_log /var/log/nginx/website/{domain_name}/bo_access.log;
    error_log /var/log/nginx/website/{domain_name}/bo_error.log;

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

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
}}
"""
            )

        # Frontend configuration (main domain)
        frontend_config_path = f"/etc/nginx/sites-available/{domain_name}"
        frontend_temp_config_path = f"/tmp/nginx_config_{domain_name}.conf"
        
        with open(frontend_temp_config_path, "w") as temp_config_file:
            temp_config_file.write(
                f"""
server {{
    listen 80;
    server_name {domain_name};

    root /var/www/static/{domain_name};
    index index.html index.htm;

    access_log /var/log/nginx/website/{domain_name}/access.log;
    error_log /var/log/nginx/website/{domain_name}/error.log;

    location / {{
        try_files $uri $uri/ =404;
    }}

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
}}

server {{
    listen 80;
    server_name www.{domain_name};
    
    access_log /var/log/nginx/website/{domain_name}/www_access.log;
    error_log /var/log/nginx/website/{domain_name}/www_error.log;
    
    return 301 http://{domain_name}$request_uri;
}}
"""
            )

        # Move configurations and set up symlinks
        run_command(f"mv {bo_temp_config_path} {bo_config_path}", elevated=True)
        run_command(f"mv {frontend_temp_config_path} {frontend_config_path}", elevated=True)

        # Remove existing symlinks if they exist
        if os.path.exists(f"/etc/nginx/sites-enabled/bo.{domain_name}"):
            run_command(f"rm /etc/nginx/sites-enabled/bo.{domain_name}", elevated=True)
        if os.path.exists(f"/etc/nginx/sites-enabled/{domain_name}"):
            run_command(f"rm /etc/nginx/sites-enabled/{domain_name}", elevated=True)

        # Create new symlinks
        run_command(
            f"ln -s {bo_config_path} /etc/nginx/sites-enabled/bo.{domain_name}",
            elevated=True,
        )
        run_command(
            f"ln -s {frontend_config_path} /etc/nginx/sites-enabled/{domain_name}",
            elevated=True,
        )
        
        run_command("systemctl reload nginx", elevated=True)
        socketio.emit("message", f"Configuration Nginx pour {domain_name} créée.")

        # Create log directory
        log_dir = f"/var/log/nginx/website/{domain_name}"
        run_command(f"mkdir -p {log_dir}", elevated=True)
        run_command(f"chown www-data:www-data {log_dir}", elevated=True)

        return True
    except Exception as e:
        socketio.emit(
            "error",
            f"Erreur lors de la création de la configuration Nginx pour {domain_name}: {str(e)}",
        )
        return False

def setup_ssl(domain_name):
    try:
        settings = load_settings()
        registrant_email = settings["registrant"]["email"]

        # Install Certbot and obtain SSL certificates individually
        domains = [f"www.{domain_name}", f"bo.{domain_name}", domain_name]
        result = ""
        for domain in domains:
            cmd_result = run_command(
                f"certbot --nginx -d {domain} --non-interactive --agree-tos -m {registrant_email}",
                elevated=True,
                return_output=True
            )
            result += cmd_result
        if "Some challenges have failed" in result:
            raise Exception("Les défis ont échoué")
        
        socketio.emit("message", f"SSL configuré pour www.{domain_name}, bo.{domain_name} et {domain_name}.")
        return True
    except Exception as e:
        socketio.emit(
            "console",
            f"Erreur lors de la configuration SSL pour www.{domain_name}, bo.{domain_name} et {domain_name}: {str(e)}",
        )
        return False

def install_wordpress(domain_name, backup_file_path=None):
    try:
        settings = load_settings()
        wp_path = f"/var/www/{domain_name}"
        
        # Ensure wp_path is clean
        if os.path.exists(wp_path):
            run_command(f"rm -rf {wp_path}", elevated=True)
        
        run_command(f"mkdir -p {wp_path}", elevated=True)
        run_command(f"chown www-data:www-data {wp_path}", elevated=True)

        # Generate random names for the database and user
        unique_db_name = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        unique_db_user = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        unique_db_password = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        registrant_email = settings["registrant"]["email"]
        wordpress_admin_email = settings.get("wordpress_admin_email", "admin@example.com")

        # Download WordPress
        if not run_command(f"wp core download --path={wp_path} --locale=fr_FR"):
            raise Exception("Échec du téléchargement de WordPress")

        # Create the database and user
        commands = [
            f"mysql -u root -e 'CREATE DATABASE {unique_db_name};'",
            f"mysql -u root -e 'CREATE USER wp_{unique_db_user}@localhost IDENTIFIED BY \"{unique_db_password}\";'",
            f"mysql -u root -e 'GRANT ALL PRIVILEGES ON {unique_db_name}.* TO wp_{unique_db_user}@localhost;'",
            f"mysql -u root -e 'FLUSH PRIVILEGES;'"
        ]
        for command in commands:
            if not run_command(command, elevated=True):
                raise Exception(f"Échec de l'exécution de la commande: {command}")

        # Create wp-config.php
        if not run_command(f"wp config create --path={wp_path} --dbname={unique_db_name} --dbuser=wp_{unique_db_user} --dbpass={unique_db_password} --dbhost=localhost --skip-check"):
            raise Exception("Échec de la création de wp-config.php")

        # Install WordPress
        if not run_command(f"wp core install --path={wp_path} --url=https://bo.{domain_name} --title='{domain_name}' --admin_user=admin --admin_password={unique_db_password} --admin_email={registrant_email} --locale=fr_FR"):
            raise Exception("Échec de l'installation de WordPress")

        # Install plugins and perform other tasks
        plugins = {
            "./vendor/aio.zip": "all-in-one-wp-migration",
            "./vendor/aio_unlimited.zip": "aio_unlimited",
            "./vendor/staatic.zip": "staatic",
            "./vendor/otomatic.zip": "otomatic-ai"
        }

        for plugin_file, plugin_name in plugins.items():
            if not run_command(f"wp plugin install {plugin_file} --path={wp_path}"):
                raise Exception(f"Échec de l'installation du plugin {plugin_name}")
            if not run_command(f"wp plugin activate {plugin_name} --path={wp_path}"):
                raise Exception(f"Échec de l'activation du plugin {plugin_name}")

        # Si un fichier de backup est fourni, le déplacer vers le nouveau répertoire temporaire
        if backup_file_path:
            tmp_backup = os.path.join("/mnt/disk2/tmp", f"{domain_name}_backup.wpress")
            if not run_command(f"mv {backup_file_path} {tmp_backup}", elevated=True):
                raise Exception("Failed to move backup file to temporary directory")
            backup_file_path = tmp_backup

        # Restore
        if run_command(f"wp ai1wm restore backup.wpress --yes --path={wp_path}"):
            socketio.emit("console", f"Restauration de backup.wpress.")
        else:
            raise Exception(f"Échec de la restauration de backup.wpress")
        # Delete the backup file after restoration
        run_command(f"rm {wp_path}/wp-content/ai1wm-backups/backup.wpress")
            
            
        # Recreate initial admin user (new complex password)
        new_admin_password = "".join(
            random.choices(string.ascii_letters + string.digits, k=16)
        )
        if not run_command(f"wp user create admin {registrant_email} --role=administrator --user_pass={new_admin_password} --path={wp_path}", ignore_errors=True):
            socketio.emit("console", "Erreur lors de la recréation de l'utilisateur administrateur initial, mais cela sera ignoré.")
            # Ignore this specific error and continue

        # Generate a simple username of up to 5 letters
        simple_username = "".join(random.choices(string.ascii_lowercase, k=5))
        simple_password = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        
        # Create a simple admin user with the email from the settings
        if not run_command(
            f"wp user create {simple_username} {wordpress_admin_email} --role=administrator --user_pass={simple_password} --path={wp_path}"
        ):
            raise Exception("Échec de la création de l'utilisateur administrateur simple")

        # Update wp cli
        if not run_command(f"wp cli update --path={wp_path}", elevated=True):
            raise Exception("Échec de la mise à jour de wp cli")

        # Install WP Login
        if not run_command(
            f"wp package install aaemnnosttv/wp-cli-login-command --path={wp_path} --url=https://bo.{domain_name}"
        ):
            raise Exception("Échec de l'installation du package WP Login")
        
        # Ensure www-data is the owner of the domain directory
        if not run_command(f"chown -R www-data:www-data {wp_path}", elevated=True):
            raise Exception("Échec du changement de propriétaire du répertoire WordPress")

        # Install Companion plugin
        result = run_command(
            f"wp login install --activate --path={wp_path} --url=https://bo.{domain_name}",
            return_output=True
        )

        if "Success: Companion plugin installed" in result:
            pass
        else:
            raise Exception("Échec de l'installation du plugin Companion")
    
        # Force Elementor data update
        try:
            run_command(f"wp elementor update db --path={wp_path}")
        except Exception as e:
            if "is not a registered wp command" in str(e):
                socketio.emit("console", "Elementor command not found, skipping Elementor data update.")
            else:
                raise Exception("Failed to update Elementor data")

        # Disable noindex
        if not run_command(f"wp option update blog_public 1 --path={wp_path}"):
            raise Exception("Échec de la désactivation de noindex")

        # Uninstall AIO, and defaults
        if not run_command(f"wp plugin uninstall aio_unlimited --deactivate --path={wp_path}"):
            raise Exception("Échec de la désinstallation du plugin AIO Unlimited")

        # Delete user 'Adrien'
        if not run_command(f"wp user delete adrien --reassign=admin --path={wp_path}"):
            raise Exception("Échec de la suppression de l'utilisateur 'Adrien'")

        # Deactivate maintenance mode
        result = run_command(f"wp maintenance-mode deactivate --path={wp_path}", return_output=True)
        if "Success: Deactivated Maintenance mode." in result:
            socketio.emit("console", "Mode maintenance désactivé avec succès.")
        elif "Maintenance mode already deactivated." in result:
            socketio.emit("console", "Le mode maintenance était déjà désactivé.")
        else:
            socketio.emit("console", f"Échec de la désactivation du mode maintenance: {result}")
            raise Exception("Échec de la désactivation du mode maintenance")
        
        # Emit success message with user details
        socketio.emit("message", f"WordPress installé pour {domain_name}. Utilisateur créé: {simple_username} avec l'email {wordpress_admin_email} et le mot de passe {simple_password}.")
        
        # Nettoyer les fichiers temporaires à la fin
        if os.path.exists(backup_file_path):
            if not run_command(f"rm -f {backup_file_path}", elevated=True):
                socketio.emit("console", f"[{domain_name}] Warning: Failed to cleanup temporary backup file")

        return True
    except Exception as e:
        socketio.emit("error", f"Erreur lors de l'installation de WordPress pour {domain_name}")
        socketio.emit("console", f"Erreur lors de l'installation de WordPress pour {domain_name}: {str(e)} (ligne: {e.__traceback__.tb_lineno})")
        return False

def generate_wp_login_link(domain_name):
    wp_path = f"/var/www/{domain_name}"
    try:
        # Vérifiez si l'utilisateur admin existe
        check_user_command = f"wp user list --field=user_login --path={wp_path}"
        user_exists = run_command(check_user_command, return_output=True)
        user_list = user_exists.strip().split("\n")
        user_list = [user.strip() for user in user_list if user]

        if "admin" not in user_list:
            # Créer un nouvel utilisateur admin si l'utilisateur n'existe pas
            new_admin_password = "".join(random.choices(string.ascii_letters + string.digits, k=16))
            create_user_command = f"wp user create admin 'admin@example.com' --role=administrator --user_pass={new_admin_password} --path={wp_path}"
            run_command(create_user_command)
        
        # Créer le lien de connexion
        command = f"wp login create admin --path={wp_path} --url=https://bo.{domain_name}"
        result = run_command(command, return_output=True)
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
    result = run_command(command, return_output=True)
    return int(result.strip()) if result else 0

def publish_article(site, title, content, image_path=None):
    wp_path = f"/var/www/{site}"
    # Escape single quotes in title and content
    title = shlex.quote(title)
    content = shlex.quote(content)
    
    # Create the post
    create_command = f"wp post create --post_type=post --post_title={title} --post_content={content} --post_status=publish --porcelain --path={shlex.quote(wp_path)}"
    post_id = run_command(create_command)
    
    if post_id:
        socketio.emit("message", f'Article "{title}" publié sur {site}.')
        
        if image_path:
            # Import the image and set it as featured image
            import_command = f"wp media import {shlex.quote(image_path)} --porcelain --path={shlex.quote(wp_path)}"
            attachment_id = run_command(import_command)
            
            if attachment_id:
                set_featured_command = f"wp post meta add {post_id.strip()} _thumbnail_id {attachment_id.strip()} --path={shlex.quote(wp_path)}"
                if run_command(set_featured_command):
                    socketio.emit("message", f'Image à la une ajoutée pour l\'article "{title}" sur {site}.')
                else:
                    socketio.emit("error", f'Erreur lors de la définition de l\'image à la une pour l\'article "{title}" sur {site}.')
            else:
                socketio.emit("error", f'Erreur lors de l\'import de l\'image pour l\'article "{title}" sur {site}.')
    else:
        socketio.emit("error", f'Erreur lors de la publication de l\'article "{title}" sur {site}.')