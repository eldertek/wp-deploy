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
        return result.stdout
    except subprocess.CalledProcessError as e:
        socketio.emit("error", f"Erreur: {e}")
        raise e
    except subprocess.TimeoutExpired as e:
        socketio.emit(
            "error", f"Timeout: La commande a pris trop de temps à s'exécuter"
        )
        raise e
    except Exception as e:
        socketio.emit("error", f"Erreur inattendue: {str(e)}")
        raise e
    return None