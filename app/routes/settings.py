from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.utils.settings import load_settings, save_settings, update_admin_password
from app.routes.site_management import admin_required

settings_bp = Blueprint('settings', __name__)

@settings_bp.route("/settings", methods=["GET", "POST"])
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
            settings["wordpress_admin_email"] = request.form.get("wordpress_admin_email", "admin@example.com").strip()

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
            flash(
                "Une erreur est survenue lors de la mise à jour des paramètres.",
                "danger",
            )
        return redirect(url_for("settings.settings"))
    return render_template("settings.html", contacts=settings)