import os
import random
import string
from app import socketio
from .system import run_command
from .settings import load_settings
import shlex

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

                # Security headers
                add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
                add_header Content-Security-Policy "default-src 'self'; script-src 'self'; object-src 'none'; style-src 'self'; img-src 'self'; media-src 'self'; frame-src 'self'; font-src 'self'; connect-src 'self';" always;
                add_header X-Frame-Options "SAMEORIGIN" always;
                add_header X-Content-Type-Options "nosniff" always;
                add_header Referrer-Policy "no-referrer-when-downgrade" always;
                add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
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
        # Install Certbot and obtain SSL certificate using HTTP-01 challenge
        result = run_command(
            f"certbot --nginx -d bo.{domain_name} --non-interactive --agree-tos -m {registrant_email}",
            elevated=True,
        )
        if "Some challenges have failed" in result:
            # Fallback to DNS-01 challenge
            result = run_command(
                f"certbot --nginx -d bo.{domain_name} --preferred-challenges dns --non-interactive --agree-tos -m {registrant_email}",
                elevated=True,
            )
            if "Some challenges have failed" in result:
                raise Exception("Both HTTP-01 and DNS-01 challenges failed")
        
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
        wordpress_admin_email = settings.get("wordpress_admin_email", "admin@example.com")

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

        # Create wp-config.php
        run_command(
            f"wp config create --path={wp_path} --dbname={unique_db_name} --dbuser=wp_{unique_db_user} --dbpass={unique_db_password} --dbhost=localhost --skip-check"
        )

        # Install WordPress
        run_command(
            f"wp core install --path={wp_path} --url=https://bo.{domain_name} --title='{domain_name}' --admin_user=admin --admin_password={unique_db_password} --admin_email={registrant_email} --locale=fr_FR"
        )

        # Install All in One Migration
        run_command(f"wp plugin install ./vendor/aio.zip --activate --path={wp_path}")
        run_command(f"wp plugin install ./vendor/aio_unlimited.zip --activate --path={wp_path}")

        # Copy vendor/wpocopo.wpress to wp-content/ai1wm-backups
        run_command(f"cp ../wpocopo.wpress {wp_path}/wp-content/ai1wm-backups/")

        # Restore
        run_command(f"wp ai1wm restore wpocopo.wpress --yes --path={wp_path}")

        # Recreate initial admin user (new complex password)
        new_admin_password = "".join(
            random.choices(string.ascii_letters + string.digits, k=16)
        )
        run_command(f"wp user create admin {registrant_email} --role=administrator --user_pass={new_admin_password} --path={wp_path}")

        # Generate a simple username of up to 5 letters
        simple_username = "".join(random.choices(string.ascii_lowercase, k=5))
        simple_password = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        
        # Create a simple admin user with the email from the settings
        run_command(
            f"wp user create {simple_username} {wordpress_admin_email} --role=administrator --user_pass={simple_password} --path={wp_path}"
        )

        socketio.emit("message", f"Utilisateur {simple_username} créé avec l'email {wordpress_admin_email} et le mot de passe {unique_db_password}.")

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
        
        # Ensure www-data is the owner of the domain directory
        run_command(f"chown -R www-data:www-data {wp_path}", elevated=True)
        
        # Disable noindex
        run_command(f"wp option update blog_public 1 --path={wp_path}")

        # Delete user 'Adrien'
        run_command(f"wp user delete adrien --reassign=admin --path={wp_path}")

        # Uninstall AIO, and defaults
        run_command(f"wp plugin uninstall aio_unlimited --deactivate --path={wp_path}")
        run_command(f"wp plugin uninstall hello --deactivate --path={wp_path}")
        run_command(f"wp plugin uninstall akismet --deactivate --path={wp_path}")

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