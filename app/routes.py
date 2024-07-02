from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user
from app import app, login_manager
from app.models import User, users, domains
from app.utils import is_domain_owned, is_domain_available, purchase_domain, configure_dns, create_nginx_config, setup_ssl, install_wordpress, generate_wp_login_link
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

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Identifiants invalides', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    sites = []
    for domain in os.listdir('/var/www/'):
        if os.path.isdir(os.path.join('/var/www/', domain)):
            site_info = {
                'domain': domain,
                'status': 'online',
                'last_deployment': 'N/A',
            }
            sites.append(site_info)
    
    return render_template('index.html', sites=sites)

@app.route('/add_domain', methods=['GET', 'POST'])
@login_required
def add_domain():
    return render_template('add_domain.html')

@app.route('/check_domain_ownership', methods=['POST'])
@login_required
def check_domain_ownership():
    domain_name = request.form['domain']
    if is_domain_owned(domain_name):
        return jsonify({'status': 'owned'})
    return jsonify({'status': 'not_owned'})

@app.route('/check_domain_availability', methods=['POST'])
@login_required
def check_domain_availability():
    domain_name = request.form['domain']
    if is_domain_available(domain_name):
        return jsonify({'status': 'available'})
    return jsonify({'status': 'not_available'})

@app.route('/purchase_domain', methods=['POST'])
@login_required
def purchase_domain_route():
    domain_name = request.form['domain']
    if purchase_domain(domain_name, load_settings()):
        return jsonify({'status': 'purchased'})
    return jsonify({'status': 'error'})

@app.route('/configure_dns', methods=['POST'])
@login_required
def configure_dns_route():
    domain_name = request.form['domain']
    if configure_dns(domain_name):
        return jsonify({'status': 'configured'})
    return jsonify({'status': 'error'})

@app.route('/create_nginx_config', methods=['POST'])
@login_required
def create_nginx_config_route():
    domain_name = request.form['domain']
    if create_nginx_config(domain_name):
        return jsonify({'status': 'created'})
    return jsonify({'status': 'error'})

@app.route('/setup_ssl', methods=['POST'])
@login_required
def setup_ssl_route():
    domain_name = request.form['domain']
    if setup_ssl(domain_name):
        return jsonify({'status': 'setup'})
    return jsonify({'status': 'error'})

@app.route('/install_wordpress', methods=['POST'])
@login_required
def install_wordpress_route():
    domain_name = request.form['domain']
    if install_wordpress(domain_name):
        return jsonify({'status': 'installed'})
    return jsonify({'status': 'error'})

@app.route('/editor', methods=['GET', 'POST'])
@login_required
def editor():
    if request.method == 'POST':
        site = request.form['site']
        title = request.form['title']
        content = request.form['content']
        publish_article(site, title, content)
        return redirect(url_for('index'))
    return render_template('editor.html', domains=domains)

@app.route('/dashboard')
@login_required
def dashboard():
    site_status = check_sites_status()
    return render_template('dashboard.html', site_status=site_status)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    settings = load_settings()
    if request.method == 'POST':
        contact_types = ['registrant', 'admin', 'technical', 'billing']
        for contact_type in contact_types:
            settings[contact_type] = {
                'firstName': request.form.get(f'{contact_type}_firstName', ''),
                'lastName': request.form.get(f'{contact_type}_lastName', ''),
                'organization': request.form.get(f'{contact_type}_organization', ''),
                'email': request.form.get(f'{contact_type}_email', ''),
                'phoneNumber': request.form.get(f'{contact_type}_phoneNumber', ''),
                'street': request.form.get(f'{contact_type}_street', ''),
                'street2': request.form.get(f'{contact_type}_street2', ''),
                'street3': request.form.get(f'{contact_type}_street3', ''),
                'city': request.form.get(f'{contact_type}_city', ''),
                'countryCode': request.form.get(f'{contact_type}_countryCode', ''),
                'postalCode': request.form.get(f'{contact_type}_postalCode', '')
            }
            if contact_type == 'registrant':
                settings[contact_type]['dotfrcontactentitytype'] = request.form.get('registrant_dotfrcontactentitytype', '')
        
        # Update other settings
        settings['mysql_password'] = request.form.get('mysql_password', '')
        settings['testapi_token'] = request.form.get('testapi_token', '')
        settings['testapi_secret'] = request.form.get('testapi_secret', '')
        settings['test_mode'] = 'test_mode' in request.form
        
        save_settings(settings)
        flash('Paramètres mise à jour avec succès', 'success')
        return redirect(url_for('settings'))
    return render_template('settings.html', contacts=settings)

@app.route('/confirm_action', methods=['POST'])
@login_required
def confirm_action():
    data = request.get_json()
    action = data.get('action')
    domain_name = data.get('domain')
    
    if action == 'create_nginx_config':
        if not create_nginx_config(domain_name, force=True):
            socketio.emit('error', f'Erreur lors de la configuration SSL pour {domain_name}.')
    elif action == 'install_wordpress':
        if not install_wordpress(domain_name, force=True):
            socketio.emit('error', f'Erreur lors de l\'installation de WordPress pour {domain_name}.')
    
    return '', 204

@app.route('/backoffice/<domain>')
@login_required
def backoffice(domain):
    login_link = generate_wp_login_link(domain)
    if login_link:
        return redirect(login_link)
    else:
        flash('Erreur lors de la génération du lien de connexion automatique', 'danger')
        return redirect(url_for('index'))

def publish_article(site, title, content):
    pass

def check_sites_status():
    return [{'domain': domain, 'status': 'online', 'last_deployment': '2023-10-01'} for domain in domains]
