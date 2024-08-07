from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.utils.wordpress import create_nginx_config, setup_ssl
from app.utils.deployment import deploy_static

debug_bp = Blueprint('debug', __name__)

@debug_bp.route("/debug", methods=["GET", "POST"])
@login_required
def debug():
    if request.method == "POST":
        domain = request.form.get("domain")
        action = request.form.get("action")
        
        if action == "nginx":
            success = create_nginx_config(domain)
            return jsonify({"status": "success" if success else "error", "message": "Action traitée par le serveur."})
        elif action == "ssl":
            success = setup_ssl(domain)
            return jsonify({"status": "success" if success else "error", "message": "Action traitée par le serveur."})
        elif action == "deploy":
            success = deploy_static(domain)  # Appel de la fonction de déploiement
            return jsonify({"status": "success" if success else "error", "message": "Déploiement forcé."})
        
    return render_template("debug.html")