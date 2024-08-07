from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from app.utils.domain import is_domain_owned, is_domain_available, purchase_domain
from app.utils.wordpress import generate_wp_login_link
from app.utils.settings import load_settings, load_sites_data
from app.utils.jobs import scheduler
from functools import wraps
import os

site_management_bp = Blueprint('site_management', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def get_domains():
    return [
        domain
        for domain in os.listdir("/var/www/")
        if os.path.isdir(os.path.join("/var/www/", domain))
        and not domain.startswith(".")
        and not domain.endswith("-static")  # Exclude domains ending with -static
    ]

@site_management_bp.route("/")
@login_required
def index():
    try:
        sites_data = load_sites_data()
        return render_template("index.html", sites=sites_data['sites'], last_update=sites_data['last_update'])
    except Exception as e:
        flash(f"Erreur lors du chargement des données des sites : {str(e)}", "danger")
        return render_template("index.html", sites=[], last_update="")

@site_management_bp.route("/add_domain", methods=["GET", "POST"])
@login_required
def add_domain():
    return render_template("add_domain.html")

@site_management_bp.route("/check_domain_ownership", methods=["GET", "POST"])
@login_required
def check_domain_ownership():
    domain_name = request.form.get("domain") if request.method == "POST" else request.args.get("domain")
    if not domain_name:
        return jsonify({"status": "error", "message": "Nom de domaine manquant"}), 400
    try:
        if is_domain_owned(domain_name):
            return jsonify({"status": "owned"})
        return jsonify({"status": "not_owned"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@site_management_bp.route("/check_domain_availability", methods=["GET", "POST"])
@login_required
def check_domain_availability():
    domain_name = request.form.get("domain") if request.method == "POST" else request.args.get("domain")
    if not domain_name:
        return jsonify({"status": "error", "message": "Nom de domaine manquant"}), 400
    try:
        availability, message = is_domain_available(domain_name)
        if availability:
            return jsonify({"status": "available", "message": message})
        return jsonify({"status": "not_available", "message": message})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@site_management_bp.route("/purchase_domain", methods=["POST"])
@login_required
def purchase_domain_route():
    domain_name = request.form.get("domain")
    if not domain_name:
        return jsonify({"status": "error", "message": "Nom de domaine manquant"}), 400
    try:
        if purchase_domain(domain_name, load_settings()):
            return jsonify({"status": "purchased"})
        return jsonify({"status": "error"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@site_management_bp.route("/backoffice/<domain>")
@login_required
def backoffice(domain):
    login_link = generate_wp_login_link(domain)
    if login_link:
        return redirect(login_link)
    else:
        flash("Erreur lors de la génération du lien de connexion automatique", "danger")
        return redirect(url_for("site_management.index"))

@site_management_bp.route("/jobs")
@login_required
def jobs():
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "name": job.name,
            "start_time": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "N/A",
        })
    return render_template("jobs.html", jobs=jobs)

@site_management_bp.route("/run_job/<job_name>", methods=["POST"])
@login_required
def run_job(job_name):
    try:
        from app.utils.jobs import run_job
        run_job(job_name)
        return jsonify({"status": "success", "message": f"Job '{job_name}' executé avec succès."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500