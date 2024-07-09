import subprocess
from app import socketio

def run_command(command, elevated=False):
    if elevated:
        command = f"sudo -s {command}"
    try:
        # Use subprocess.run with timeout and capture_output for better control
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True, timeout=300
        )
        return True  # Command succeeded
    except subprocess.CalledProcessError as e:
        # Emit both stdout and stderr in case of error
        socketio.emit("error", f"Erreur: {e}\nSortie: {e.stdout}\nErreur: {e.stderr}")
        return False  # Command failed
    except subprocess.TimeoutExpired as e:
        socketio.emit(
            "error", f"Timeout: La commande a pris trop de temps à s'exécuter"
        )
        return False  # Command timed out
    except Exception as e:
        socketio.emit("error", f"Erreur inattendue: {str(e)}")
        return False  # Unexpected error
    return None