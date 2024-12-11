import subprocess
from app import socketio
import os

def run_command(command, elevated=False, return_output=False, ignore_errors=False):
    if elevated:
        command = f"sudo -s bash -c '{command}'"
    
    try:
        env = os.environ.copy()
        env['TMPDIR'] = '/tmp'
        
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            env=env
        )
        
        if return_output:
            return result.stdout
        return True
        
    except subprocess.CalledProcessError as e:
        if not ignore_errors:
            socketio.emit("console", f"Erreur: {e}\nSortie: {e.stdout}\nErreur: {e.stderr}")
            return f"Erreur: {e}\nSortie: {e.stdout}\nErreur: {e.stderr}"
        return ignore_errors
        
    except Exception as e:
        if not ignore_errors:
            socketio.emit("console", f"Erreur inattendue: {str(e)}")
            return f"Erreur inattendue: {str(e)}"
        return ignore_errors