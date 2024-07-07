from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.utils.wordpress import publish_article
import os
from werkzeug.utils import secure_filename

editor_bp = Blueprint('editor', __name__)

@editor_bp.route("/editor", methods=["GET", "POST"])
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
                return redirect(url_for("site_management.index"))
            except Exception as e:
                flash(
                    "Une erreur est survenue lors de la publication de l'article",
                    "danger",
                )
                return redirect(url_for("editor.editor"))
        else:
            flash("Site invalide", "danger")
            return redirect(url_for("editor.editor"))

    selected_site = request.args.get("site")
    if selected_site and selected_site not in domains:
        flash("Site invalide", "danger")
        return redirect(url_for("site_management.index"))

    return render_template("editor.html", domains=domains, selected_site=selected_site)