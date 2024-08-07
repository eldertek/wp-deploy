import subprocess
from app import socketio
import asyncio

def run_command(command, elevated=False, return_output=False):
    if elevated:
        command = f"sudo -s {command}"
    try:
        # Use subprocess.run without a timeout for long-running commands
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        if return_output:
            return result.stdout  # Return the command output
        else:
            return True  # Command succeeded without needing to return output
    except subprocess.CalledProcessError as e:
        # Emit both stdout and stderr in case of error
        socketio.emit("console", f"Erreur: {e}\nSortie: {e.stdout}\nErreur: {e.stderr}")
        return False  # Command failed
    except Exception as e:
        socketio.emit("console", f"Erreur inattendue: {str(e)}")
        return False  # Unexpected error
