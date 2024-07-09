import subprocess
from app import socketio

def run_command(command, elevated=False, return_output=False, timeout=300):
    if elevated:
        command = f"sudo -s {command}"
    try:
        # Use subprocess.run with timeout and capture_output for better control
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True, timeout=timeout
        )
        if return_output:
            return result.stdout  # Return the command output
        else:
            return True  # Command succeeded without needing to return output
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