from apscheduler.schedulers.background import BackgroundScheduler
import pytz
from .deployment import deploy_static, log_deployment, update_sites_data
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
    domains = [domain for domain in os.listdir('/var/www/') if os.path.isdir(os.path.join('/var/www/', domain)) and not domain.startswith('.')]
    for domain in domains:
        success = deploy_static(domain)
        duration = (datetime.datetime.now() - start_time).total_seconds()
        log_deployment(domain, success, duration)

def update_indexed_articles():
    update_sites_data(indexed=True)

def update_sites_basic_data():
    update_sites_data(indexed=False)

# Initialize the scheduler
scheduler = create_scheduler()

# Start the scheduler
def start_scheduler():
    scheduler.start()

# Shutdown the scheduler
def shutdown_scheduler():
    scheduler.shutdown()