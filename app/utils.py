from internetbs import Domain, DNS

api_key = 'testapi'
password = 'testpass'
test_mode = True

domain = Domain(api_key, password, test_mode)
dns = DNS(api_key, password, test_mode)

def is_domain_owned(domain_name):
    domains = domain.list_domains()
    for d in domains:
        if d.domain_name == domain_name:
            return True
    return False

def is_domain_available(domain_name):
    return domain.check_availability(domain_name)

# TODO : settings needed to records, contacts detail for registration
def purchase_domain(domain_name):
    return domain.create_domain(domain_name)

def configure_dns(domain_name, type, value):
    # Delete record to avoid error if already exists
    try:
        dns.remove_record(domain_name, type, value)
    except Exception:
        pass
    # Add new record
    return dns.add_record(domain_name, type, value)

# TODO : find nginx sites_available, create a new one with the domain_name, link it to sites_enabled (for a future wordpress installation)
def create_nginx_config(domain_name):
    pass

# TODO : configure ssl with certbot
def setup_ssl(domain_name):
    pass

# TODO : install wordpress autonomously
def install_wordpress(domain_name):
    pass