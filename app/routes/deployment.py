from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.routes.domains import load_domains
from app.utils.deployment import deploy_static
from app.utils.domain import configure_dns, check_dns
from app.utils.wordpress import create_nginx_config, setup_ssl, install_wordpress
from app import socketio
import datetime
import os
import json
import re

deployment_bp = Blueprint('deployment', __name__)

def handle_deployment_route(domain_name, deployment_function):
    if not domain_name or not re.match(r'^[a-zA-Z0-9.-]+$', domain_name):
        return jsonify({"status": "error", "message": "Nom de domaine invalide"}), 400
    start_time = datetime.datetime.now()
    try:
        if deployment_function(domain_name):
            return jsonify({"status": "success"})
        return jsonify({"status": "error"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@deployment_bp.route("/deploy_all", methods=["POST"])
@login_required
def deploy_all():
    domains = [
        domain
        for domain in os.listdir("/var/www/")
        if os.path.isdir(os.path.join("/var/www/", domain))
        and not domain.startswith(".")
        and not domain.endswith("-static")  # Exclude domains ending with -static
    ]
    for domain in domains:
        try:
            deploy_static(domain)
        except Exception as e:
            socketio.emit("error", f"Error deploying {domain}: {str(e)}")
    return jsonify({"status": "deployed"})

@deployment_bp.route("/deploy_site", methods=["POST"])
@login_required
def deploy_site():
    domain = request.json.get('domain')
    if domain.endswith("-static"):  # Exclude domains ending with -static
        return jsonify({"status": "error", "message": "Nom de domaine invalide"}), 400
    return handle_deployment_route(domain, deploy_static)

@deployment_bp.route("/deployments")
@login_required
def deployments():
    log_path = "data/deployments.json"
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as log_file:
                deployments = json.load(log_file)
        except json.JSONDecodeError:
            # Initialize the JSON file if it is invalid or does not exist
            deployments = []
            with open(log_path, "w") as log_file:
                json.dump(deployments, log_file, indent=4)
            socketio.emit("console", "Le fichier de log est corrompu ou vide. Un nouveau fichier a été créé.")
    else:
        deployments = []
    return render_template("deployments.html", deployments=deployments)

@deployment_bp.route("/configure_dns", methods=["POST"])
@login_required
def configure_dns_route():
    domain_name = request.form.get("domain")
    return handle_deployment_route(domain_name, configure_dns)

@deployment_bp.route("/create_nginx_config", methods=["POST"])
@login_required
def create_nginx_config_route():
    domain_name = request.form.get("domain")
    return handle_deployment_route(domain_name, create_nginx_config)

@deployment_bp.route("/setup_ssl", methods=["POST"])
@login_required
def setup_ssl_route():
    domain_name = request.form.get("domain")
    return handle_deployment_route(domain_name, setup_ssl)

@deployment_bp.route("/install_wordpress", methods=["POST"])
@login_required
def install_wordpress_route():
    domain_name = request.form.get("domain")
    backup_file = request.files.get("backupFile")
    
    if backup_file:
        # Sauvegarder temporairement le fichier
        backup_file_path = f"/tmp/{domain_name}_backup.wpress"
        backup_file.save(backup_file_path)
    else:
        backup_file_path = None

    try:
        if install_wordpress(domain_name, backup_file_path):
            if backup_file_path:
                os.remove(backup_file_path)  # Nettoyer le fichier temporaire
            return jsonify({"status": "success"})
        return jsonify({"status": "error"})
    except Exception as e:
        if backup_file_path:
            os.remove(backup_file_path)  # Nettoyer le fichier temporaire en cas d'erreur
        return jsonify({"status": "error", "message": str(e)}), 500

@deployment_bp.route("/deploy_static", methods=["POST"])
@login_required
def deploy_static_route():
    domain_name = request.form.get("domain")
    return handle_deployment_route(domain_name, deploy_static)

@deployment_bp.route("/check_dns", methods=["POST"])
@login_required
def check_dns_route():
    domain_name = request.form.get("domain")
    if not domain_name or not re.match(r'^[a-zA-Z0-9.-]+$', domain_name):  # Added regex validation for domain
        return jsonify({"status": "error", "message": "Nom de domaine invalide"}), 400
    try:
        # Check if the domain is configured
        if not any(d["name"] == domain_name and d["status"] == "Configuré" for d in load_domains()):
            return jsonify({
                "status": "error",
                "message": "Le domaine doit être configuré avant de pouvoir installer Wordpress (Menu 'Domaines')."
            })
        
        if check_dns(domain_name):
            socketio.emit("message", f"Le DNS pour {domain_name} est correctement configuré.")
            return jsonify({"status": "valid"})
        return jsonify({"status": "error"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@deployment_bp.route("/delete_logs_yesterday", methods=["POST"])
@login_required
def delete_logs_yesterday():
    log_path = "data/deployments.json"
    if os.path.exists(log_path):
        with open(log_path, "r") as log_file:
            logs = json.load(log_file)
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        logs = [log for log in logs if datetime.datetime.fromtimestamp(log["timestamp"]) > yesterday]
        with open(log_path, "w") as log_file:
            json.dump(logs, log_file, indent=4)
    return jsonify({"status": "success"})

@deployment_bp.route("/delete_logs_last_week", methods=["POST"])
@login_required
def delete_logs_last_week():
    log_path = "data/deployments.json"
    if os.path.exists(log_path):
        with open(log_path, "r") as log_file:
            logs = json.load(log_file)
        last_week = datetime.datetime.now() - datetime.timedelta(weeks=1)
        logs = [log for log in logs if datetime.datetime.fromtimestamp(log["timestamp"]) > last_week]
        with open(log_path, "w") as log_file:
            json.dump(logs, log_file, indent=4)
    return jsonify({"status": "success"})

@deployment_bp.route("/delete_logs_last_month", methods=["POST"])
@login_required
def delete_logs_last_month():
    log_path = "data/deployments.json"
    if os.path.exists(log_path):
        with open(log_path, "r") as log_file:
            logs = json.load(log_file)
        last_month = datetime.datetime.now() - datetime.timedelta(days=30)
        logs = [log for log in logs if datetime.datetime.fromtimestamp(log["timestamp"]) > last_month]
        with open(log_path, "w") as log_file:
            json.dump(logs, log_file, indent=4)
    return jsonify({"status": "success"})
