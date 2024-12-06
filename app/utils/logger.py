import logging
import os
from logging.handlers import RotatingFileHandler
import datetime

class TaskLogger:
    def __init__(self):
        # Créer le dossier de logs s'il n'existe pas
        self.log_dir = '/var/log/wp-deploy'
        os.makedirs(self.log_dir, exist_ok=True)

        # Logger pour les erreurs
        self.error_logger = self._setup_logger(
            'error_logger',
            os.path.join(self.log_dir, 'error.log'),
            logging.ERROR
        )

        # Logger pour les accès/infos
        self.access_logger = self._setup_logger(
            'access_logger',
            os.path.join(self.log_dir, 'access.log'),
            logging.INFO
        )

    def _setup_logger(self, name, log_file, level):
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        handler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)
        
        return logger

    def log_task_start(self, task_name, domain=None):
        msg = f"Démarrage de la tâche: {task_name}"
        if domain:
            msg += f" pour le domaine: {domain}"
        self.access_logger.info(msg)

    def log_task_end(self, task_name, domain=None, duration=None, success=True):
        msg = f"Fin de la tâche: {task_name}"
        if domain:
            msg += f" pour le domaine: {domain}"
        if duration:
            msg += f" (durée: {duration:.2f}s)"
        msg += f" - Statut: {'Succès' if success else 'Échec'}"
        self.access_logger.info(msg)

    def log_error(self, task_name, error_msg, domain=None):
        msg = f"Erreur dans la tâche {task_name}"
        if domain:
            msg += f" pour le domaine: {domain}"
        msg += f": {error_msg}"
        self.error_logger.error(msg)

# Créer une instance globale du logger
task_logger = TaskLogger() 