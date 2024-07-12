from internetbs import Domain, DNS
from app import socketio
from .settings import load_settings
import dns.resolver

settings = load_settings()
api_key = settings["internetbs_token"]
password = settings["internetbs_password"]
test_mode = settings["test_mode"]

domain_client = Domain(api_key, password, test_mode)
dns_client = DNS(api_key, password, test_mode)

def is_domain_owned(domain_name):
    socketio.emit(
        "message", f"Vérification de la possession du domaine {domain_name}..."
    )
    domains = domain_client.list_domains()
    for d in domains:
        if d.domain_name == domain_name:
            socketio.emit("message", f"Domaine {domain_name} est déjà possédé.")
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
        {
            "name": f"bo.{domain_name}",
            "type": "AAAA",
            "value": "2001:41d0:304:200::5ec6",
        },
        {"name": f"{domain_name}", "type": "A", "value": "185.199.108.153"},
        {"name": f"{domain_name}", "type": "AAAA", "value": "2606:50c0:8000::153"},
    ]

    for record in dns_records:
        try:
            dns_client.remove_record(record["name"], record["type"])
        except Exception:
            pass
        try:
            result = dns_client.add_record(record["name"], record["type"], record["value"])
            socketio.emit(
                "message",
                f'Enregistrement DNS {record["type"]} pour {record["name"]} configuré à {record["value"]}.',
            )
        except Exception as e:
            socketio.emit(
                "error",
                f'Erreur lors de la configuration DNS {record["type"]} pour {record["name"]}: {str(e)}',
            )
            return None
    return True

def check_dns(domain_name):
    expected_records = [
        {"name": f"bo.{domain_name}", "type": "A", "value": "51.210.255.66"},
        {"name": f"bo.{domain_name}", "type": "AAAA", "value": "2001:41d0:304:200::5ec6"},
        {"name": f"{domain_name}", "type": "A", "value": "185.199.108.153"},
        {"name": f"{domain_name}", "type": "AAAA", "value": "2606:50c0:8000::153"},
    ]

    try:
        for record in expected_records:
            answers = dns.resolver.resolve(record["name"], record["type"])
            found = False
            for rdata in answers:
                if rdata.to_text() == record["value"]:
                    found = True
                    break
            if not found:
                socketio.emit(
                    "error",
                    f'Enregistrement DNS {record["type"]} pour {record["name"]} avec valeur {record["value"]} est manquant ou incorrect.'
                )
                return False
        return True
    except Exception as e:
        error_message = f"Erreur lors de la vérification DNS pour {domain_name}: {str(e)}"
        if "The DNS query name does not exist" in str(e):
            error_message = f"Le domaine {domain_name} ou l'un de ses sous-domaines n'existe pas."
        socketio.emit("error", error_message)
        return False