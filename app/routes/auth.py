from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from app.models import User
from app.utils.settings import verify_admin_credentials

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("site_management.index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and verify_admin_credentials(username, password):
            user = User(username)
            login_user(user)
            return redirect(url_for("site_management.index"))
        else:
            flash("Identifiants invalides", "danger")
    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))