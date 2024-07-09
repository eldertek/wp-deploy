from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required
from app.utils.deployment import deploy_static, log_deployment, format_deployment_log
from app.utils.domain import configure_dns, check_dns
from app.utils.wordpress import create_nginx_config, setup_ssl, install_wordpress
from app.utils.git import initialize_git_repo
from app import socketio
import datetime
import os
import json

deployment_bp = Blueprint('deployment', __name__)

@deployment_bp.route("/deploy_all", methods=["POST"])
@login_required
def deploy_all():
    start_time = datetime.datetime.now()
    domains = [
        domain
        for domain in os.listdir("/var/www/")
        if os.path.isdir(os.path.join("/var/www/", domain))
        and not domain.startswith(".")
    ]
    for domain in domains:
        try:
            success = deploy_static(domain)
            duration = (datetime.datetime.now() - start_time).total_seconds()
            log_deployment(domain, success, duration)
        except Exception as e:
            socketio.emit("error", f"Error deploying {domain}: {str(e)}")
    return jsonify({"status": "deployed"})

@deployment_bp.route("/confirm_action", methods=["POST"])
@login_required
def confirm_action():
    data = request.get_json()
    action = data.get("action")
    domain_name = data.get("domain")

    if action == "create_nginx_config":
        if not create_nginx_config(domain_name, force=True):
            socketio.emit(
                "error", f"Erreur lors de la configuration SSL pour {domain_name}."
            )
    elif action == "install_wordpress":
        if not install_wordpress(domain_name, force=True):
            socketio.emit(
                "error",
                f"Erreur lors de l'installation de WordPress pour {domain_name}.",
            )

    return "", 204

@deployment_bp.route("/deploy_site", methods=["POST"])
@login_required
def deploy_site():
    socketio.emit("message", "Déploiement en cours...")
    domain = request.json.get('domain')
    start_time = datetime.datetime.now()
    try:
        success = deploy_static(domain)
        duration = (datetime.datetime.now() - start_time).total_seconds()
        log_deployment(domain, success, duration)
        if success:
            socketio.emit("message", f"Le site {domain} a été déployé avec succès.")
        else:
            socketio.emit("error", f"Erreur lors du déploiement du site {domain}.")
    except Exception as e:
        socketio.emit("error", f"Erreur lors du déploiement du site {domain} : {str(e)}")
    return redirect(url_for("site_management.index"))

@deployment_bp.route("/deployments")
@login_required
def deployments():
    log_path = "data/deployments.json"
    if os.path.exists(log_path):
        with open(log_path, "r") as log_file:
            deployments = json.load(log_file)
            deployments = [
                format_deployment_log(deployment) for deployment in deployments
            ]
    else:
        deployments = []
    return render_template("deployments.html", deployments=deployments)

@deployment_bp.route("/configure_dns", methods=["POST"])
@login_required
def configure_dns_route():
    domain_name = request.form.get("domain")
    if not domain_name:
        return jsonify({"status": "error", "message": "Nom de domaine manquant"}), 400
    try:
        if configure_dns(domain_name):
            return jsonify({"status": "configured"})
        return jsonify({"status": "error"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@deployment_bp.route("/create_nginx_config", methods=["POST"])
@login_required
def create_nginx_config_route():
    domain_name = request.form.get("domain")
    if not domain_name:
        return jsonify({"status": "error", "message": "Nom de domaine manquant"}), 400
    try:
        if create_nginx_config(domain_name):
            return jsonify({"status": "created"})
        return jsonify({"status": "error"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@deployment_bp.route("/setup_ssl", methods=["POST"])
@login_required
def setup_ssl_route():
    domain_name = request.form.get("domain")
    if not domain_name:
        return jsonify({"status": "error", "message": "Nom de domaine manquant"}), 400
    try:
        if setup_ssl(domain_name):
            return jsonify({"status": "setup"})
        return jsonify({"status": "error", "restart": True})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@deployment_bp.route("/install_wordpress", methods=["POST"])
@login_required
def install_wordpress_route():
    domain_name = request.form.get("domain")
    if not domain_name:
        return jsonify({"status": "error", "message": "Nom de domaine manquant"}), 400
    try:
        success, restart = install_wordpress(domain_name)
        if success:
            return jsonify({"status": "installed"})
        if restart:
            return jsonify({"status": "error", "restart": True})
        return jsonify({"status": "error"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@deployment_bp.route("/initialize_git_repo", methods=["POST"])
@login_required
def initialize_git_repo_route():
    domain_name = request.form.get("domain")
    if not domain_name:
        return jsonify({"status": "error", "message": "Nom de domaine manquant"}), 400
    try:
        if initialize_git_repo(domain_name):
            return jsonify({"status": "initialized"})
        return jsonify({"status": "error"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@deployment_bp.route("/deploy_static", methods=["POST"])
@login_required
def deploy_static_route():
    domain_name = request.form.get("domain")
    if not domain_name:
        return jsonify({"status": "error", "message": "Nom de domaine manquant"}), 400
    start_time = datetime.datetime.now()
    try:
        success = deploy_static(domain_name)
        duration = (datetime.datetime.now() - start_time).total_seconds()
        log_deployment(domain_name, success, duration)
        if success:
            return jsonify({"status": "deployed"})
        return jsonify({"status": "error"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@deployment_bp.route("/check_dns", methods=["POST"])
@login_required
def check_dns_route():
    domain_name = request.form.get("domain")
    if not domain_name:
        return jsonify({"status": "error", "message": "Nom de domaine manquant"}), 400
    try:
        if check_dns(domain_name):
            socketio.emit("message", f"Le DNS pour {domain_name} est correctement configuré.")
            return jsonify({"status": "valid"})
        return jsonify({"status": "error"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500