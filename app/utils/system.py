import subprocess
from app import socketio
import os
import tempfile

def run_command(command, elevated=False, return_output=False, ignore_errors=False):
    if elevated:
        # Use readlink to resolve symlinks in the command path
        command = f"sudo -s bash -c '{command}'"
    
    # Create a temporary directory specifically for this command
    with tempfile.TemporaryDirectory(prefix='wp_deploy_', dir='/var/tmp') as tmp_dir:
        try:
            env = os.environ.copy()
            env['TMPDIR'] = tmp_dir
            
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