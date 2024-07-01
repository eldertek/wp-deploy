from internetbs import Domain, DNS
from app import socketio
import json, os

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
    result = domain.create_domain(domain_name, contacts)
    socketio.emit('message', f'Domaine {domain_name} a été acheté.')
    return result

def configure_dns(domain_name, type, value):
    try:
        dns.remove_record(domain_name, type, value)
    except Exception:
        pass
    result = dns.add_record(domain_name, type, value)
    socketio.emit('message', f'Enregistrement DNS {type} pour {domain_name} configuré à {value}.')
    return result

def create_nginx_config(domain_name):
    config = f"""
    server {{
        listen 80;
        server_name {domain_name};

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
    config_path = f"/etc/nginx/sites-available/{domain_name}"
    with open(config_path, 'w') as f:
        f.write(config)
    
    if os.path.exists(f"/etc/nginx/sites-enabled/{domain_name}"):
        os.remove(f"/etc/nginx/sites-enabled/{domain_name}")
    
    os.symlink(config_path, f"/etc/nginx/sites-enabled/{domain_name}")
    socketio.emit('message', f'Configuration Nginx pour {domain_name} créée.')
    os.system('systemctl reload nginx')

def setup_ssl(domain_name):
    settings = load_settings()
    registrant_email = settings['registrant']['email']
    # Install Certbot and obtain SSL certificate
    os.system(f"certbot --nginx -d {domain_name} --non-interactive --agree-tos -m {registrant_email}")
    socketio.emit('message', f'SSL configuré pour {domain_name}.')

def install_wordpress(domain_name):
    settings = load_settings()
    mysql_password = settings['mysql_password']
    
    # Define the path where WordPress will be installed
    wp_path = f"/var/www/{domain_name}"
    
    # Download WordPress
    os.system(f"wp core download --path={wp_path}")
    
    # Create wp-config.php
    unique_db_name = f"wordpress_{domain_name.replace('.', '_')}"
    os.system(f"wp config create --path={wp_path} --dbname={unique_db_name} --dbuser=root --dbpass={mysql_password} --dbhost=localhost --skip-check")
    
    # Install WordPress
    os.system(f"wp core install --path={wp_path} --url=https://{domain_name} --title='My WordPress Site' --admin_user=admin --admin_password=admin_password --admin_email=admin@example.com")
    
    socketio.emit('message', f'WordPress installé pour {domain_name}.')
