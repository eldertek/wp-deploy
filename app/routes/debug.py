from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.utils.wordpress import create_nginx_config, setup_ssl
from app.utils.deployment import deploy_static
from app.utils.domain import configure_dns
import os

debug_bp = Blueprint('debug', __name__)

@debug_bp.route("/debug", methods=["GET", "POST"])
@login_required
def debug():
    if request.method == "POST":
        domain = request.form.get("domain")
        action = request.form.get("action")
        
        if domain == "*":
            domains = [domain for domain in os.listdir('/var/www/') 
                      if os.path.isdir(os.path.join('/var/www/', domain)) 
                      and not domain.startswith('.')]
            results = []
            for domain in domains:
                result = execute_action(domain, action)
                results.append(result)
            return jsonify(results)
        else:
            result = execute_action(domain, action)
            return jsonify(result)
    
    return render_template("debug.html")

def execute_action(domain, action):
    if action == "nginx":
        success = create_nginx_config(domain)
        return {"status": "success" if success else "error", "message": f"Nginx configuré pour {domain}."}
    elif action == "ssl":
        success = setup_ssl(domain)
        return {"status": "success" if success else "error", "message": f"SSL configuré pour {domain}."}
    elif action == "deploy":
        success = deploy_static(domain)
        return {"status": "success" if success else "error", "message": f"Déploiement forcé pour {domain}."}
    elif action == "dns":
        success = configure_dns(domain)
        return {"status": "success" if success else "error", "message": f"DNS configuré pour {domain}."}