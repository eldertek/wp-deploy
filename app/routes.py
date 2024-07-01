from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user
from app import app, login_manager
from app.models import User, users, domains
from app.utils import is_domain_owned, is_domain_available, purchase_domain, configure_dns, create_nginx_config, setup_ssl, install_wordpress
from flask_socketio import SocketIO, emit

socketio = SocketIO(app)

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
        if is_domain_owned(domain_name):
            socketio.emit('message', 'Vérification de la possession du domaine....OK')
        else:
            # Step 2: Check domain availability
            if is_domain_available(domain_name):
                socketio.emit('message', 'Vérification de la disponibilité du domaine...OK')

                # Step 3: Purchase domain
                purchase_domain(domain_name)
                socketio.emit('message', 'Achat du nom de domaine...OK')
            
        # Step 4: Configure DNS
        configure_dns(domain_name, 'A', '51.210.255.66')
        configure_dns(domain_name, 'AAAA', '2001:41d0:304:200::5ec6')
        socketio.emit('message', 'Paramètrages DNS vers le serveur...OK')
            
        # Step 5: Create Nginx configuration
        create_nginx_config(domain_name)
        socketio.emit('message', 'Création des fichiers de configuration Nginx...OK')
            
        # Step 6: Setup SSL
        setup_ssl(domain_name)
        socketio.emit('message', 'Paramètres du SSL...OK')
            
        # Step 7: Install WordPress
        install_wordpress(domain_name)
        socketio.emit('message', 'Installation de Wordpress...OK')
            
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

def publish_article(site, title, content):
    pass

def check_sites_status():
    return [{'domain': domain, 'status': 'online', 'last_deployment': '2023-10-01'} for domain in domains]
