from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user
from app import app, login_manager
from app.models import User, users, domains
from app.utils import is_domain_owned, is_domain_available, purchase_domain, configure_dns, create_nginx_config, setup_ssl, install_wordpress
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
    return render_template('index.html')

@app.route('/add_domain', methods=['GET', 'POST'])
@login_required
def add_domain():
    if request.method == 'POST':
        domain_name = request.form['domain']
        
        # Step 1: Check domain ownership
        if not is_domain_owned(domain_name):
            # Step 2: Check domain availability
            if is_domain_available(domain_name):
                # Step 3: Purchase domain
                if not purchase_domain(domain_name, load_settings()):
                    return render_template('add_domain.html')
                socketio.emit('message', 'Achat du nom de domaine...OK')
            else:
                return render_template('add_domain.html')
        
        # Step 4: Configure DNS
        if not configure_dns(domain_name, 'A', '51.210.255.66'):
            return render_template('add_domain.html')
        if not configure_dns(domain_name, 'AAAA', '2001:41d0:304:200::5ec6'):
            return render_template('add_domain.html')
            
        # Step 5: Create Nginx configuration
        if not create_nginx_config(domain_name):
            return render_template('add_domain.html')
            
        # Step 6: Setup SSL
        if not setup_ssl(domain_name):
            return render_template('add_domain.html')
            
        # Step 7: Install WordPress
        if not install_wordpress(domain_name):
            return render_template('add_domain.html')
            
        socketio.emit('message', "L'installation est terminée")
    return render_template('add_domain.html')

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
    action = request.form['action']
    domain_name = request.form['domain']
    
    if action == 'create_nginx_config':
        if create_nginx_config(domain_name):
            socketio.emit('message', f'Configuration Nginx pour {domain_name} créée.')
    elif action == 'install_wordpress':
        if install_wordpress(domain_name):
            socketio.emit('message', f'WordPress installé pour {domain_name}.')
    
    return '', 204

def publish_article(site, title, content):
    pass

def check_sites_status():
    return [{'domain': domain, 'status': 'online', 'last_deployment': '2023-10-01'} for domain in domains]
