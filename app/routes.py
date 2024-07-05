from flask import render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_user, login_required, logout_user, current_user

from app import app, socketio, scheduler
from app.models import User
from app.utils import (
    is_domain_owned,
    is_domain_available,
    purchase_domain,
    configure_dns,
    create_nginx_config,
    setup_ssl,
    install_wordpress,
    generate_wp_login_link,
    publish_article,
    initialize_git_repo,
    deploy_static,
    log_deployment,
    fetch_site_data,
    format_deployment_log,
    load_settings,
    save_settings,
    verify_admin_credentials,
    update_admin_password,
    update_published_articles_data,
    update_indexed_articles_data,
    update_last_update_time
)
import json, os, datetime
from functools import wraps
import logging
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != "admin":
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and verify_admin_credentials(username, password):
            user = User(username)
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("Identifiants invalides", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/jobs")
@login_required
def jobs():
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "name": job.name,
            "start_time": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "N/A",
        })
    return render_template("jobs.html", jobs=jobs)


@app.route("/")
@login_required
def index():
    try:
        sites = fetch_site_data()
        
        if not os.path.exists("data/last_update.json"):
            # Forcer une actualisation manuelle
            update_published_articles_data()
            update_indexed_articles_data()
            update_last_update_time()
        
        with open("data/last_update.json", "r") as f:
            last_update_data = json.load(f)
        last_update = last_update_data["last_update"]

        return render_template("index.html", sites=sites, last_update=last_update)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash("Une erreur est survenue lors du chargement des données.", "danger")
        return redirect(url_for("login"))


@app.route("/add_domain", methods=["GET", "POST"])
@login_required
def add_domain():
    return render_template("add_domain.html")


@app.route("/check_domain_ownership", methods=["GET", "POST"])
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
        logger.error(f"Error checking domain ownership: {str(e)}")
        return jsonify({"status": "error", "message": "Une erreur est survenue"}), 500


@app.route("/check_domain_availability", methods=["GET", "POST"])
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


@app.route("/purchase_domain", methods=["POST"])
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
        logger.error(f"Error purchasing domain: {str(e)}")
        return jsonify({"status": "error", "message": "Une erreur est survenue"}), 500


@app.route("/configure_dns", methods=["POST"])
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
        logger.error(f"Error configuring DNS: {str(e)}")
        return jsonify({"status": "error", "message": "Une erreur est survenue"}), 500


@app.route("/create_nginx_config", methods=["POST"])
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
        logger.error(f"Error creating nginx config: {str(e)}")
        return jsonify({"status": "error", "message": "Une erreur est survenue"}), 500


@app.route("/setup_ssl", methods=["POST"])
@login_required
def setup_ssl_route():
    domain_name = request.form.get("domain")
    if not domain_name:
        return jsonify({"status": "error", "message": "Nom de domaine manquant"}), 400
    try:
        if setup_ssl(domain_name):
            return jsonify({"status": "setup"})
        return jsonify({"status": "error"})
    except Exception as e:
        logger.error(f"Error setting up SSL: {str(e)}")
        return jsonify({"status": "error", "message": "Une erreur est survenue"}), 500


@app.route("/deploy_all", methods=["POST"])
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
            logger.error(f"Error deploying {domain}: {str(e)}")
    return jsonify({"status": "deployed"})


@app.route("/install_wordpress", methods=["POST"])
@login_required
def install_wordpress_route():
    domain_name = request.form.get("domain")
    if not domain_name:
        return jsonify({"status": "error", "message": "Nom de domaine manquant"}), 400
    try:
        if install_wordpress(domain_name):
            return jsonify({"status": "installed"})
        return jsonify({"status": "error"})
    except Exception as e:
        logger.error(f"Error installing WordPress: {str(e)}")
        return jsonify({"status": "error", "message": "Une erreur est survenue"}), 500


@app.route("/initialize_git_repo", methods=["POST"])
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
        logger.error(f"Error initializing Git repo: {str(e)}")
        return jsonify({"status": "error", "message": "Une erreur est survenue"}), 500


@app.route("/deploy_static", methods=["POST"])
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
        logger.error(f"Error deploying {domain_name}: {str(e)}")
        return jsonify({"status": "error", "message": "Une erreur est survenue"}), 500


@app.route("/editor", methods=["GET", "POST"])
@login_required
def editor():
    domains = [
        domain
        for domain in os.listdir("/var/www/")
        if os.path.isdir(os.path.join("/var/www/", domain))
        and not domain.startswith(".")
    ]

    if request.method == "POST":
        site = request.form.get("site")
        title = request.form.get("title")
        content = request.form.get("content")
        featured_image = request.files.get("featured_image")
        
        if site in domains:
            try:
                image_path = None
                if featured_image and featured_image.filename:
                    filename = secure_filename(featured_image.filename)
                    upload_dir = f"/tmp"
                    if not os.path.exists(upload_dir):
                        os.makedirs(upload_dir)
                    image_path = os.path.join(upload_dir, filename)
                    featured_image.save(image_path)
                
                publish_article(site, title, content, image_path)
                return redirect(url_for("index"))
            except Exception as e:
                logger.error(f"Error publishing article: {str(e)}")
                flash(
                    "Une erreur est survenue lors de la publication de l'article",
                    "danger",
                )
                return redirect(url_for("editor"))
        else:
            flash("Site invalide", "danger")
            return redirect(url_for("editor"))

    selected_site = request.args.get("site")
    if selected_site and selected_site not in domains:
        flash("Site invalide", "danger")
        return redirect(url_for("index"))

    return render_template("editor.html", domains=domains, selected_site=selected_site)


@app.route("/settings", methods=["GET", "POST"])
@login_required
@admin_required
def settings():
    settings = load_settings()
    if request.method == "POST":
        try:
            contact_types = ["registrant", "admin", "technical", "billing"]
            for contact_type in contact_types:
                settings[contact_type] = {
                    key: request.form.get(f"{contact_type}_{key}", "").strip()
                    for key in [
                        "firstName",
                        "lastName",
                        "organization",
                        "email",
                        "phoneNumber",
                        "street",
                        "street2",
                        "street3",
                        "city",
                        "countryCode",
                        "postalCode",
                    ]
                }
                if contact_type == "registrant":
                    settings[contact_type]["dotfrcontactentitytype"] = request.form.get(
                        "registrant_dotfrcontactentitytype", ""
                    ).strip()

            settings["internetbs_token"] = request.form.get(
                "internetbs_token", "testapi"
            ).strip()
            settings["internetbs_password"] = request.form.get(
                "internetbs_password", "testpass"
            ).strip()
            settings["github_username"] = request.form.get(
                "github_username", ""
            ).strip()
            settings["github_token"] = request.form.get("github_token", "").strip()
            settings["test_mode"] = request.form.get("test_mode", True)

            # Update admin password if provided
            new_admin_password = request.form.get("admin_password", "").strip()
            if new_admin_password:
                if update_admin_password("admin", new_admin_password):
                    flash("Le mot de passe de l'administrateur a été mis à jour avec succès", "success")
                else:
                    flash("Erreur lors de la mise à jour du mot de passe de l'administrateur", "danger")

            save_settings(settings)
            flash("Paramètres mis à jour avec succès", "success")
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            flash(
                "Une erreur est survenue lors de la mise à jour des paramètres.",
                "danger",
            )
        return redirect(url_for("settings"))
    return render_template("settings.html", contacts=settings)


@app.route("/confirm_action", methods=["POST"])
@login_required
@admin_required
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


@app.route("/backoffice/<domain>")
@login_required
def backoffice(domain):
    login_link = generate_wp_login_link(domain)
    if login_link:
        return redirect(login_link)
    else:
        flash("Erreur lors de la génération du lien de connexion automatique", "danger")
        return redirect(url_for("index"))


@app.route("/deployments")
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

