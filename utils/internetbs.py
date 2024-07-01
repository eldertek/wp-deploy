from internetbs-api import Domain

api_key = 'testapi'
password = 'testpass'
test_mode = True

domain = Domain(api_key, password, test_mode)

def check_domain_availability(domain_name):
    result = domain.check_availability(domain_name)
    return result
