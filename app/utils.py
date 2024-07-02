from internetbs import Domain, DNS
from app import socketio
import json, os
import subprocess
import random
import string

def load_settings():
    config_path = 'app/config.json'
    model_path = 'app/settings.json'
    
    if not os.path.exists(config_path):
        with open(model_path, 'r') as model_file:
            settings = json.load(model_file)
        save_settings(settings)
        
    if os.path.exists(config_path):
        with open(config_path, 'r') as config_file:
            return json.load(config_file)
    else:
        return {}

def save_settings(settings):
    config_path = 'app/config.json'
    with open(config_path, 'w') as config_file:
        json.dump(settings, config_file, indent=4)

# Load settings
settings = load_settings()
api_key = settings['testapi_token']
password = settings['testapi_secret']
test_mode = settings['test_mode']

domain = Domain(api_key, password, test_mode)
dns = DNS(api_key, password, test_mode)

def load_settings():
    with open('app/settings.json', 'r') as f:
        return json.load(f)

def is_domain_owned(domain_name):
    socketio.emit('message', f'Vérification de la possession du domaine {domain_name}...')
    domains = domain.list_domains()
    for d in domains:
        if d.domain_name == domain_name:
            socketio.emit('message', f'Domaine {domain_name} est déjà possédé.')
            return True
    return False

def is_domain_available(domain_name):
    available = domain.check_availability(domain_name)
    socketio.emit('message', f'Domaine {domain_name} est disponible.' if available else f'Domaine {domain_name} n\'est pas disponible.')
    return available

def purchase_domain(domain_name, contacts):
    try:
        result = domain.create_domain(domain_name, contacts)
        socketio.emit('message', f'Domaine {domain_name} a été acheté.')
        return result
    except Exception as e:
        socketio.emit('error', f'Erreur lors de l\'achat du domaine {domain_name}: {str(e)}')
        return None

def configure_dns(domain_name, type, value):
    bo_domain_name = f"bo.{domain_name}"
    try:
        dns.remove_record(bo_domain_name, type, value)
    except Exception:
        pass
    try:
        result = dns.add_record(bo_domain_name, type, value)
        socketio.emit('message', f'Enregistrement DNS {type} pour {bo_domain_name} configuré à {value}.')
        return result
    except Exception as e:
        socketio.emit('error', f'Erreur lors de la configuration DNS {type} pour {bo_domain_name}: {str(e)}')
        return None

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        socketio.emit('error', f'Erreur: {e.stderr.decode("utf-8")}')
        return None

def create_nginx_config(domain_name, force=False):
    try:
        config_path = f"/etc/nginx/sites-available/bo.{domain_name}"
        if os.path.exists(config_path) and not force:
            socketio.emit('confirm', {'message': f'Configuration Nginx pour bo.{domain_name} existe déjà. Voulez-vous continuer ?', 'action': 'create_nginx_config'})
            return False
        
        config = f"""
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
        with open(config_path, 'w') as f:
            f.write(config)
        
        if os.path.exists(f"/etc/nginx/sites-enabled/bo.{domain_name}"):
            os.remove(f"/etc/nginx/sites-enabled/bo.{domain_name}")
        
        os.symlink(config_path, f"/etc/nginx/sites-enabled/bo.{domain_name}")
        run_command('systemctl reload nginx')
        socketio.emit('message', f'Configuration Nginx pour bo.{domain_name} créée.')
        
        return True
    except Exception as e:
        socketio.emit('error', f'Erreur lors de la création de la configuration Nginx pour bo.{domain_name}: {str(e)}')
        return False

def setup_ssl(domain_name):
    try:
        settings = load_settings()
        registrant_email = settings['registrant']['email']
        # Install Certbot and obtain SSL certificate
        run_command(f"certbot --nginx -d bo.{domain_name} --non-interactive --agree-tos -m {registrant_email}")
        socketio.emit('message', f'SSL configuré pour bo.{domain_name}.')
        return True
    except Exception as e:
        socketio.emit('error', f'Erreur lors de la configuration SSL pour bo.{domain_name}: {str(e)}')
        return False

def install_wordpress(domain_name, force=False):
    try:
        wp_path = f"/var/www/{domain_name}"
        if os.path.exists(wp_path):
            if not force:
                socketio.emit('confirm', {'message': f'WordPress est déjà installé pour {domain_name}. Voulez-vous continuer ?', 'action': 'install_wordpress'})
                return False
            else:
                run_command(f"rm -rf {wp_path}")
        
        # Generate random names for the database and user
        unique_db_name = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        unique_db_user = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        unique_db_password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        # Download WordPress
        run_command(f"wp core download --allow-root --path={wp_path}")

        # Create the database
        run_command(f"mysql -u root -e 'CREATE DATABASE {unique_db_name};'")

        # Create a unique user for WordPress
        run_command(f"mysql -u root -e 'CREATE USER wp_{unique_db_user}@localhost IDENTIFIED BY \"{unique_db_password}\";'")
        run_command(f"mysql -u root -e 'GRANT ALL PRIVILEGES ON {unique_db_name}.* TO wp_{unique_db_user}@localhost;'")
        run_command(f"mysql -u root -e 'FLUSH PRIVILEGES;'")

        socketio.emit('message', f'Base de données WordPress {unique_db_name} créée avec le mot de passe {unique_db_password} pour wp_{unique_db_user}.')
        
        # Create wp-config.php
        run_command(f"wp config create --allow-root --path={wp_path} --dbname={unique_db_name} --dbuser=wp_{unique_db_user} --dbpass={unique_db_password} --dbhost=localhost --skip-check")
        
        # Install WordPress
        run_command(f"wp core install --allow-root --path={wp_path} --url=https://{domain_name} --title='My WordPress Site' --admin_user=admin --admin_password=admin --admin_email=admin@example.com")
        
        socketio.emit('message', f'WordPress installé pour {domain_name}.')
        return True
    except Exception as e:
        socketio.emit('error', f'Erreur lors de l\'installation de WordPress pour {domain_name}: {str(e)}')
        return False
