import os
import json
import requests
from app import socketio
from .system import run_command
from .settings import load_settings

def initialize_git_repo(domain_name):
    repo_path = f"/opt/websites/{domain_name}"
    try:
        if os.path.exists(repo_path):
            run_command(f"rm -rf {repo_path}", elevated=True)
        os.makedirs(repo_path)

        # Initialize a local git repository
        run_command(f"git init {repo_path}")

        # Create a CNAME file with the domain name
        cname_path = os.path.join(repo_path, "CNAME")
        with open(cname_path, "w") as cname_file:
            cname_file.write(domain_name)

        # Add and commit the CNAME file
        run_command(
            f"cd {repo_path} && git add CNAME && git commit -m 'Add CNAME file'"
        )

        settings = load_settings()
        github_token = settings["github_token"]
        github_username = settings["github_username"]

        # Check if the repository already exists and delete it if it does
        response = requests.get(
            f"https://api.github.com/repos/{github_username}/{domain_name}",
            headers={
                "Authorization": f"token {github_token}",
                "Content-Type": "application/json",
            },
        )
        if response.status_code == 200:
            run_command(
                f"curl -X DELETE -H 'Authorization: token {github_token}' https://api.github.com/repos/{github_username}/{domain_name}"
            )

        # Create a GitHub repository
        run_command(
            f"curl -X POST -H 'Authorization: token {github_token}' -H 'Content-Type: application/json' -d '{{ \"name\": \"{domain_name}\" }}' https://api.github.com/user/repos"
        )

        # Add the remote origin and push the initial commit
        run_command(
            f"cd {repo_path} && git remote add origin https://{github_token}@github.com/{github_username}/{domain_name}.git"
        )
        run_command(f"cd {repo_path} && git push -u origin master")

        # Enable GitHub Pages with SSL
        pages_data = {"source": {"branch": "master", "path": "/"}}
        run_command(
            f"curl -X POST -H 'Authorization: token {github_token}' -H 'Content-Type: application/json' -d '{json.dumps(pages_data)}' https://api.github.com/repos/{github_username}/{domain_name}/pages"
        )

        # Enforce HTTPS
        run_command(
            f"curl -X PATCH -H 'Authorization: token {github_token}' -H 'Content-Type: application/json' -d '{{ \"enforce_https\": true }}' https://api.github.com/repos/{github_username}/{domain_name}"
        )

        socketio.emit(
            "message",
            f"Dépôt GitHub {domain_name} créé, initialisé avec un fichier CNAME, et GitHub Pages activé avec SSL.",
        )
        return True
    except Exception as e:
        socketio.emit(
            "error",
            f"Erreur lors de l'initialisation du dépôt Git pour {domain_name}: {str(e)}",
        )
        return False