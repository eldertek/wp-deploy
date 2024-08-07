from app import app
from .auth import auth_bp
from .site_management import site_management_bp
from .editor import editor_bp
from .settings import settings_bp
from .deployment import deployment_bp
from .domains import domains_bp
from .debug import debug_bp

app.register_blueprint(auth_bp)
app.register_blueprint(debug_bp)
app.register_blueprint(site_management_bp)
app.register_blueprint(editor_bp)
app.register_blueprint(domains_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(deployment_bp)