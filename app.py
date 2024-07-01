from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

app = Flask(__name__)
app.secret_key = 'your_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "info"

# In-memory storage for simplicity
users = {'admin': {'password': 'password'}}
domains = []
articles = []

class User(UserMixin):
    def __init__(self, id):
        self.id = id

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
        domain = request.form['domain']
        availability = check_domain_availability(domain)
        if availability['status'] == 'available':
            flash('Domaine disponible', 'success')
        else:
            flash('Domaine non disponible', 'danger')
        return redirect(url_for('index'))
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

if __name__ == '__main__':
    app.run(debug=True)
