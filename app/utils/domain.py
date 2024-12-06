from internetbs import Domain, DNS, Host
from app import socketio
from .settings import load_settings
from .system import run_command
import dns.resolver

settings = load_settings()
api_key = settings["internetbs_token"]
password = settings["internetbs_password"]
test_mode = settings["test_mode"]

domain_client = Domain(api_key, password, test_mode)
dns_client = DNS(api_key, password, test_mode)
host_client = Host(api_key, password, test_mode)

def is_domain_owned(domain_name):
    socketio.emit(
        "message", f"Vérification de la possession du domaine {domain_name}..."
    )
    domains, api_url = domain_client.list_domains()
    for d in domains:
        if d.domain_name == domain_name:
            socketio.emit("message", f"Domaine {domain_name} est déjà possédé.")
            socketio.emit("console", f"Domaine {domain_name} est déjà possédé. -> {api_url}")
            return True
    return False

def is_domain_available(domain_name):
    try:
        available = domain_client.check_availability(domain_name)
        message = f"Le domaine {domain_name} est {'disponible' if available else 'non disponible'}."
        socketio.emit("message", message)
        return available, message
    except Exception as e:
        error_message = f"Erreur lors de la vérification de la disponibilité de {domain_name}: {str(e)}"
        socketio.emit("error", error_message)
        raise Exception(error_message)

def purchase_domain(domain_name, contacts):
    try:
        result = domain_client.create_domain(domain_name, contacts)
        socketio.emit("message", f"Domaine {domain_name} a été acheté.")
        return result
    except Exception as e:
        socketio.emit(
            "error", f"Erreur lors de l'achat du domaine {domain_name}: {str(e)}"
        )
        return None

def configure_dns(domain_name):
    expected_records = [
        {"name": f"bo.{domain_name}", "type": "A", "value": "51.210.255.66"},
        {"name": f"bo.{domain_name}", "type": "AAAA", "value": "2001:41d0:304:200::5ec6"},
        {"name": f"{domain_name}", "type": "A", "value": "51.210.255.66"},
        {"name": f"{domain_name}", "type": "AAAA", "value": "2001:41d0:304:200::5ec6"},
        {"name": f"www.{domain_name}", "type": "A", "value": "51.210.255.66"},
        {"name": f"www.{domain_name}", "type": "AAAA", "value": "2001:41d0:304:200::5ec6"},
    ]
    ns_records = ["ns-usa.topdns.com", "ns-canada.topdns.com", "ns-uk.topdns.com"]

    resolver = dns.resolver.Resolver()
    resolver.cache = dns.resolver.LRUCache(0)
    try:
        current_ns_records = [rdata.target.to_text(omit_final_dot=True) for rdata in resolver.resolve(domain_name, 'NS')]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        current_ns_records = []
    except Exception as e:
        socketio.emit("console", f"{domain_name} - Erreur lors de la récupération des NS: {str(e)}")
        current_ns_records = []

    if set(current_ns_records) != set(ns_records): # NS Server Incorrect - Add NS Records
        socketio.emit("message", f"Les serveurs de noms sont incorrects. Configuration en cours...")
        # Loop to add all records, try, catch
        for record in ns_records:
            try:
                dns_client.add_record(domain_name, "NS", record)
                socketio.emit("console", f"{domain_name} - {record} ajouté.")
            except Exception as e:
                socketio.emit("error", "Les serveurs de noms ne sont pas configurés correctement. Veuillez patienter quelques minutes puis réessayez.")
                socketio.emit("console", f"{domain_name} - {record} - Erreur lors de l'ajout de l'enregistrement DNS: {str(e)}")
                raise Exception(f"{domain_name} - {record} - Erreur lors de l'ajout de l'enregistrement DNS: {str(e)}")

        # Update Domain, try, catch
        try:
            domain_client.update_domain(domain_name, ns_list=ns_records)
            socketio.emit("message", "Les serveurs de noms ont été configurés avec succès. Merci de patienter quelques minutes puis réessayez.")
        except Exception as e:
            socketio.emit("console", f"{domain_name} - Erreur lors de la mise à jour du domaine: {str(e)}")
            socketio.emit("error", "Erreur lors de la mise à jour du domaine. Veuillez patienter quelques minutes puis réessayez.")
    else: # NS Server Correct - Add DNS Records
        # Loop two times to remove all records, try, catch
        for _ in range(2):
            for record in expected_records:
                try:
                    dns_client.remove_record(record["name"], record["type"])
                except Exception as e:
                    pass

        socketio.emit("message", "Les serveurs de noms sont corrects. Configuration en cours...")
        for record in expected_records:
            try:
                dns_client.add_record(record["name"], record["type"], record["value"])
                
            except Exception as e:
                socketio.emit("error", f"Erreur lors de l'ajout de l'enregistrement DNS: {str(e)}")
        socketio.emit("message", "Les enregistrements DNS ont été configurés avec succès. Merci de patienter quelques minutes puis procédez à la vérification.")
        return True

def check_dns(domain_name):
    expected_records = [
        {"name": f"bo.{domain_name}", "type": "A", "value": "51.210.255.66"},
        {"name": f"bo.{domain_name}", "type": "AAAA", "value": "2001:41d0:304:200::5ec6"},
        {"name": f"{domain_name}", "type": "A", "value": "51.210.255.66"},
        {"name": f"{domain_name}", "type": "AAAA", "value": "2001:41d0:304:200::5ec6"},
    ]

    try:
        resolver = dns.resolver.Resolver()
        resolver.cache = dns.resolver.LRUCache(0)
        for record in expected_records:
            answers = resolver.resolve(record["name"], record["type"])
            if not any(rdata.to_text() == record["value"] for rdata in answers):
                socketio.emit(
                    "error",
                    f'Enregistrement DNS {record["type"]} pour {record["name"]} avec valeur {record["value"]} est manquant ou incorrect. Il peut être nécessaire d\'attendre la propagation DNS.'
                )
                return False
        return True
    except Exception as e:
        error_message = f"Erreur lors de la vérification DNS pour {domain_name}: {str(e)}"
        if ("The DNS response does not contain an answer to the question" in str(e)) or ("The DNS query name does not exist" in str(e)):
            error_message = f"La configuration DNS pour {domain_name} est incorrecte. Si vous venez de configurer le DNS, attendez quelques heures et réessayez."
        socketio.emit("error", error_message)
        socketio.emit("console", f"Erreur lors de la vérification DNS pour {domain_name}: {str(e)}")
        return False