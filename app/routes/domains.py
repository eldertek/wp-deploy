from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.utils.domain import is_domain_owned, is_domain_available, purchase_domain, configure_dns, check_dns
from app.utils.settings import load_settings, save_settings
import json
import os
from werkzeug.utils import secure_filename

domains_bp = Blueprint('domains', __name__)

@domains_bp.route("/domains")
@login_required
def domains():
    return render_template("domains.html")

@domains_bp.route("/domains/get")
@login_required
def get_domains():
    domains = load_domains()
    return jsonify({"domains": domains})

@domains_bp.route("/domains/add", methods=["POST"])
@login_required
def add_domain():
    domain = request.form.get("domain")
    registrar = request.form.get("registrar")
    backup_file = request.files.get("backupFile")

    # Vérifiez si le fichier de sauvegarde est fourni
    if backup_file:
        backup_file_path = f"/tmp/{secure_filename(backup_file.filename)}"
        backup_file.save(backup_file_path)

        # Vérifiez l'espace disque ou d'autres erreurs
        if os.path.getsize(backup_file_path) > 20 * 1024 * 1024 * 1024:  # Limite de 20 Go
            return jsonify({"status": "error", "message": "Le fichier de sauvegarde est trop volumineux."}), 400

    domains = load_domains()
    if any(d["name"] == domain for d in domains):
        return jsonify({"status": "error", "message": "Domaine déjà existant"})
    
    if registrar == 'internetbs':
        if is_domain_owned(domain):
            save_domain(domain, "En attente de configuration")
            return jsonify({"status": "success", "domain": {"name": domain, "status": "En attente de configuration"}})
        
        available, message = is_domain_available(domain)
        if not available:
            return jsonify({"status": "error", "message": message})
        
        settings = load_settings()
        if purchase_domain(domain, settings):
            save_domain(domain, "En attente de configuration")
            return jsonify({"status": "success", "domain": {"name": domain, "status": "En attente de configuration"}})
        else:
            return jsonify({"status": "error", "message": "Erreur lors de l'achat du domaine."})
    else:
        # Change status to "En attente de vérification" for other registrars
        save_domain(domain, "En attente de vérification")
        return jsonify({"status": "success", "domain": {"name": domain, "status": "En attente de vérification"}})

@domains_bp.route("/domains/configure", methods=["POST"])
@login_required
def configure_domain():
    domain = request.form.get("domain")
    domains = load_domains()
    current_status = next((d["status"] for d in domains if d["name"] == domain), None)

    if current_status == "En attente de vérification":
        if check_dns(domain):
            update_domain_status(domain, "Configuré")
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "La configuration DNS n'est pas encore correcte. Il est possible que le DNS n'ait pas encore propagé. Veuillez attendre quelques heures et réessayer."})
    else:
        if configure_dns(domain):
            update_domain_status(domain, "En attente de vérification")
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Erreur lors de la configuration DNS."})

@domains_bp.route("/domains/delete", methods=["POST"])
@login_required
def delete_domain():
    domain = request.form.get("domain")
    domains = load_domains()
    domains = [d for d in domains if d["name"] != domain]
    
    with open('data/domains.json', 'w') as f:
        json.dump(domains, f)
    
    return jsonify({"status": "success"})

def load_domains():
    if os.path.exists('data/domains.json'):
        with open('data/domains.json', 'r') as f:
            return json.load(f)
    return []

def save_domain(domain, status):
    domains = load_domains()
    domains.append({"name": domain, "status": status})
    with open('data/domains.json', 'w') as f:
        json.dump(domains, f)

def update_domain_status(domain, status):
    domains = load_domains()
    for d in domains:
        if d["name"] == domain:
            d["status"] = status
            break
    with open('data/domains.json', 'w') as f:
        json.dump(domains, f)