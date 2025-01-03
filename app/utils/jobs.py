from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor
import pytz
from app import socketio
from .deployment import deploy_static, update_sites_data, delete_old_deployment_logs
import datetime
import os
from app.utils.logger import task_logger
import time

def create_scheduler():
    scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/Paris'))
    
    # Add jobs to the scheduler
    scheduler.add_job(deploy_all_websites, 'cron', hour=0, minute=0)
    scheduler.add_job(update_indexed_articles, 'cron', hour=0, minute=0)
    scheduler.add_job(update_sites_basic_data, 'cron', hour='6-23', minute=0)
    
    return scheduler

def deploy_all_websites():
    task_logger.log_task_start("deploy_all_websites")
    start_time = time.time()
    
    try:
        domains = [domain for domain in os.listdir('/var/www/') 
                  if os.path.isdir(os.path.join('/var/www/', domain)) 
                  and not domain.startswith('.')
                  and not domain == 'static']
        
        total_domains = len(domains)
        socketio.emit("console", f"Déploiement de {total_domains} sites")
        task_logger.access_logger.info(f"Début du déploiement pour {total_domains} sites")

        # Utiliser ThreadPoolExecutor avec max_workers=3
        with ThreadPoolExecutor(max_workers=3) as executor:
            for index, domain in enumerate(domains, 1):
                try:
                    progress = (index / total_domains) * 100
                    status_msg = f"[{index}/{total_domains}] ({progress:.1f}%) Déploiement de {domain}"
                    socketio.emit("console", status_msg)
                    task_logger.access_logger.info(status_msg)
                    
                    # Soumettre le travail à l'executor
                    future = executor.submit(deploy_static, domain)
                    
                except Exception as e:
                    error_msg = f"Erreur lors du déploiement de {domain}: {str(e)}"
                    socketio.emit("error", error_msg)
                    task_logger.log_error("deploy_all_websites", error_msg, domain)
                    continue

        duration = time.time() - start_time
        success_msg = f"Déploiement de tous les sites terminé en {duration:.2f}s"
        socketio.emit("console", success_msg)
        task_logger.log_task_end("deploy_all_websites", duration=duration)
        
    except Exception as e:
        error_msg = f"Erreur critique lors du déploiement: {str(e)}"
        socketio.emit("error", error_msg)
        task_logger.log_error("deploy_all_websites", error_msg)
        raise

    delete_old_deployment_logs()

def update_indexed_articles():
    task_logger.log_task_start("update_indexed_articles")
    start_time = time.time()
    
    try:
        domains = [domain for domain in os.listdir('/var/www/') 
                  if os.path.isdir(os.path.join('/var/www/', domain)) 
                  and not domain.startswith('.')
                  and not domain == 'static']
        
        total_domains = len(domains)
        socketio.emit("console", f"Mise à jour des données d'indexation pour {total_domains} sites")
        task_logger.access_logger.info(f"Début de la mise à jour d'indexation pour {total_domains} sites")

        for index, domain in enumerate(domains, 1):
            try:
                progress = (index / total_domains) * 100
                status_msg = f"[{index}/{total_domains}] ({progress:.1f}%) Indexation de {domain}"
                socketio.emit("console", status_msg)
                task_logger.access_logger.info(status_msg)
                
                # Mesurer le temps pour chaque domaine
                domain_start = time.time()
                update_sites_data(indexed=True, specific_domain=domain)
                domain_duration = time.time() - domain_start
                
                task_logger.access_logger.info(f"Indexation de {domain} terminée en {domain_duration:.2f}s")
                
            except Exception as e:
                error_msg = f"Erreur lors de l'indexation de {domain}: {str(e)}"
                socketio.emit("error", error_msg)
                task_logger.log_error("update_indexed_articles", error_msg, domain)
                continue

        duration = time.time() - start_time
        success_msg = f"Mise à jour des indexations terminée en {duration:.2f}s"
        socketio.emit("console", success_msg)
        task_logger.log_task_end("update_indexed_articles", duration=duration)
        
    except Exception as e:
        error_msg = f"Erreur critique lors de l'indexation: {str(e)}"
        socketio.emit("error", error_msg)
        task_logger.log_error("update_indexed_articles", error_msg)
        raise

def update_sites_basic_data():
    task_logger.log_task_start("update_sites_basic_data")
    start_time = time.time()
    
    try:
        domains = [domain for domain in os.listdir('/var/www/') 
                  if os.path.isdir(os.path.join('/var/www/', domain)) 
                  and not domain.startswith('.')
                  and not domain == 'static']
        
        total_domains = len(domains)
        socketio.emit("console", f"Mise à jour des données pour {total_domains} sites")
        task_logger.access_logger.info(f"Début de la mise à jour pour {total_domains} sites")

        for index, domain in enumerate(domains, 1):
            try:
                progress = (index / total_domains) * 100
                status_msg = f"[{index}/{total_domains}] ({progress:.1f}%) Traitement de {domain}"
                socketio.emit("console", status_msg)
                task_logger.access_logger.info(status_msg)
                
                # Mesurer le temps pour chaque domaine
                domain_start = time.time()
                update_sites_data(indexed=False, specific_domain=domain)
                domain_duration = time.time() - domain_start
                
                task_logger.access_logger.info(f"Domaine {domain} traité en {domain_duration:.2f}s")
                
            except Exception as e:
                error_msg = f"Erreur lors du traitement de {domain}: {str(e)}"
                socketio.emit("error", error_msg)
                task_logger.log_error("update_sites_basic_data", error_msg, domain)
                continue

        duration = time.time() - start_time
        success_msg = f"Mise à jour terminée en {duration:.2f}s"
        socketio.emit("console", success_msg)
        task_logger.log_task_end("update_sites_basic_data", duration=duration)
        
    except Exception as e:
        error_msg = f"Erreur critique: {str(e)}"
        socketio.emit("error", error_msg)
        task_logger.log_error("update_sites_basic_data", error_msg)
        raise

def run_job(job_name):
    start_time = time.time()
    task_logger.log_task_start(job_name)
    
    try:
        job = scheduler.get_job(job_name)
        if job:
            task_logger.log_task_start(f"Exécution via scheduler: {job_name}")
            result = job.func(*job.args, **job.kwargs)
        else:
            task_logger.log_task_start(f"Exécution directe: {job_name}")
            if job_name == "update_indexed_articles":
                result = update_indexed_articles()
            elif job_name == "deploy_all_websites":
                result = deploy_all_websites()
            elif job_name == "update_sites_basic_data":
                result = update_sites_basic_data()
            else:
                error_msg = f"Job non reconnu: {job_name}"
                task_logger.log_error(job_name, error_msg)
                raise ValueError(error_msg)

        duration = time.time() - start_time
        task_logger.log_task_end(job_name, duration=duration, success=True)
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        task_logger.log_error(job_name, str(e))
        task_logger.log_task_end(job_name, duration=duration, success=False)
        raise

# Initialize the scheduler
scheduler = create_scheduler()

# Start the scheduler
def start_scheduler():
    scheduler.start()

# Shutdown the scheduler
def shutdown_scheduler():
    scheduler.shutdown()
