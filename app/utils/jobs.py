from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor
import pytz
from .deployment import deploy_static, update_sites_data, delete_old_deployment_logs
import datetime
import os

def create_scheduler():
    scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/Paris'))
    
    # Add jobs to the scheduler
    scheduler.add_job(deploy_all_websites, 'cron', hour=0, minute=0)
    scheduler.add_job(update_indexed_articles, 'cron', hour=0, minute=0)
    scheduler.add_job(update_sites_basic_data, 'interval', minutes=5)
    
    return scheduler

def deploy_all_websites():
    start_time = datetime.datetime.now()
    domains = [domain for domain in os.listdir('/var/www/') if os.path.isdir(os.path.join('/var/www/', domain)) and not domain.startswith('.') and not domain.endswith('-static')]
    
    # Use ThreadPoolExecutor to deploy websites in parallel
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(deploy_static, domain): domain for domain in domains}
    
    delete_old_deployment_logs()

def update_indexed_articles():
    update_sites_data(indexed=True)

def update_sites_basic_data():
    update_sites_data(indexed=False)

def run_job(job_name):
    job = scheduler.get_job(job_name)
    if job:
        job.func(*job.args, **job.kwargs)  # Exécutez la fonction du job
    else:
        # Si le job n'est pas trouvé, essayez de l'exécuter manuellement
        if job_name == "update_indexed_articles":
            update_indexed_articles()
        elif job_name == "deploy_all_websites":
            deploy_all_websites()
        elif job_name == "update_sites_basic_data":
            update_sites_basic_data()
        else:
            raise ValueError("Job non reconnu.")

# Initialize the scheduler
scheduler = create_scheduler()

# Start the scheduler
def start_scheduler():
    scheduler.start()

# Shutdown the scheduler
def shutdown_scheduler():
    scheduler.shutdown()
