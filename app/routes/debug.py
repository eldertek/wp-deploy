from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.utils.wordpress import create_nginx_config, setup_ssl
from app.utils.deployment import deploy_static, update_sites_data
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
                      and not domain.startswith('.')
                      and not domain == 'static']
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
    elif action == "update_basic":
        try:
            update_sites_data(indexed=False, specific_domain=domain)
            return {"status": "success", "message": f"Mise à jour basique effectuée pour {domain}."}
        except Exception as e:
            return {"status": "error", "message": f"Erreur lors de la mise à jour basique de {domain}: {str(e)}"}
    elif action == "update_indexed":
        try:
            update_sites_data(indexed=True, specific_domain=domain)
            return {"status": "success", "message": f"Mise à jour de l'indexation effectuée pour {domain}."}
        except Exception as e:
            return {"status": "error", "message": f"Erreur lors de la mise à jour de l'indexation de {domain}: {str(e)}"}