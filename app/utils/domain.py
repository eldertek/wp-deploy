from internetbs import Domain, DNS, Host
from app import socketio
from .settings import load_settings
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
    dns_records = [
        {"name": f"bo.{domain_name}", "type": "A", "value": "51.210.255.66"},
        {"name": f"bo.{domain_name}", "type": "AAAA", "value": "2001:41d0:304:200::5ec6"},
        {"name": domain_name, "type": "A", "value": "51.210.255.66"},
        {"name": domain_name, "type": "AAAA", "value": "2001:41d0:304:200::5ec6"},
        {"name": domain_name, "type": "NS", "value": "ns-canada.topdns.com."},
        {"name": domain_name, "type": "NS", "value": "ns-uk.topdns.com."},
        {"name": domain_name, "type": "NS", "value": "ns-usa.topdns.com."},
    ]

    for _ in range(3):
        for record in dns_records:
            try:
                dns_client.remove_record(record["name"], record["type"])
            except Exception:
                pass
    
    try:
        current_ns = [rdata.to_text() for rdata in dns.resolver.resolve(domain_name, 'NS')]
        expected_ns = [record["value"] for record in dns_records if record["type"] == "NS"]

        if not all(ns in current_ns for ns in expected_ns):
            socketio.emit("message", f"Les enregistrements NS pour {domain_name} ne sont pas corrects. Création des enregistrements NS...")
            for record in [r for r in dns_records if r["type"] == "NS"]:
                api_response, api_url = dns_client.add_record(record["name"], record["type"], record["value"])
                socketio.emit("console", f"DNS : {record['name']} {record['type']} {record['value']} -> {api_url}")
                socketio.emit("console", f"DNS Response: {api_response}")
                socketio.emit("message", f'Enregistrement DNS NS pour {domain_name} configuré à {record["value"]}.')
            socketio.emit("error", "Veuillez réessayer plus tard après la propagation DNS. (cela peut prendre plusieurs heures)")
            return None

    except dns.resolver.NXDOMAIN:
        socketio.emit("message", f"Le domaine {domain_name} n'existe pas. Création des enregistrements NS...")
        for record in [r for r in dns_records if r["type"] == "NS"]:
            api_response, api_url = dns_client.add_record(record["name"], record["type"], record["value"])
            socketio.emit("console", f"DNS : {record['name']} {record['type']} {record['value']} -> {api_url}")
            socketio.emit("console", f"DNS Response: {api_response}")
            socketio.emit("message", f'Enregistrement DNS NS pour {domain_name} configuré à {record["value"]}.')
        socketio.emit("error", "Veuillez réessayer plus tard après la propagation DNS. (cela peut prendre plusieurs heures)")
        return None

    except dns.resolver.NoAnswer:
        socketio.emit("message", f"Pas de réponse NS pour {domain_name}. Création des enregistrements NS...")
        for record in [r for r in dns_records if r["type"] == "NS"]:
            api_response, api_url = dns_client.add_record(record["name"], record["type"], record["value"])
            socketio.emit("console", f"DNS : {record['name']} {record['type']} {record['value']} -> {api_url}")
            socketio.emit("console", f"DNS Response: {api_response}")
            socketio.emit("message", f'Enregistrement DNS NS pour {domain_name} configuré à {record["value"]}.')
        socketio.emit("error", "Veuillez réessayer plus tard après la propagation DNS. (cela peut prendre plusieurs heures)")
        return None

    except Exception as e:
        socketio.emit("error", f'Erreur lors de la vérification des enregistrements NS pour {domain_name}, merci de réessayer dans quelques minutes.')
        socketio.emit("console", f"Erreur lors de la vérification des enregistrements NS pour {domain_name}: {str(e)}")
        return None

    socketio.emit("message", f"Configuration du DNS pour {domain_name}...")

    try:
        for record in dns_records:
            api_response, api_url = dns_client.add_record(record["name"], record["type"], record["value"])
            socketio.emit("console", f"DNS : {record['name']} {record['type']} {record['value']} -> {api_url}")
            socketio.emit("console", f"DNS Response: {api_response}")
            socketio.emit("message", f'Enregistrement DNS {record["type"]} pour {record["name"]} configuré à {record["value"]}.')
    except Exception as e:
        socketio.emit("error", f'Erreur lors de la configuration DNS pour {domain_name}: {str(e)}')
        return None
    return True

def check_dns(domain_name):
    expected_records = [
        {"name": f"bo.{domain_name}", "type": "A", "value": "51.210.255.66"},
        {"name": f"bo.{domain_name}", "type": "AAAA", "value": "2001:41d0:304:200::5ec6"},
        {"name": f"{domain_name}", "type": "A", "value": "51.210.255.66"},
        {"name": f"{domain_name}", "type": "AAAA", "value": "2001:41d0:304:200::5ec6"},
    ]

    try:
        for record in expected_records:
            answers = dns.resolver.resolve(record["name"], record["type"])
            if not any(rdata.to_text() == record["value"] for rdata in answers):
                socketio.emit(
                    "error",
                    f'Enregistrement DNS {record["type"]} pour {record["name"]} avec valeur {record["value"]} est manquant ou incorrect. Il peut être nécessaire d\'attendre la propagation DNS.'
                )
                return False
        return True
    except Exception as e:
        error_message = f"Erreur lors de la vérification DNS pour {domain_name}: {str(e)}"
        if "The DNS response does not contain an answer to the question" in str(e):
            error_message = f"La configuration DNS pour {domain_name} est incorrecte. Si vous venez de configurer le DNS, attendez quelques heures et réessayez."
        socketio.emit("error", error_message)
        socketio.emit("console", f"Erreur lors de la vérification DNS pour {domain_name}: {str(e)}")
        return False