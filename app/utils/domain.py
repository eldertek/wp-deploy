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
    zone_file_path = f"/etc/bind/db.{domain_name}"
    temp_zone_file_path = f"/tmp/db.{domain_name}"

    # Create DNS configuration file
    with open(temp_zone_file_path, "w") as temp_zone_file:
        temp_zone_file.write(f"$TTL 86400\n")
        temp_zone_file.write(f"@   IN  SOA ns1.a1b2c3d4e5.fr. admin.chinavisum24.de. (\n")
        temp_zone_file.write(f"            2023081001  ; Serial\n")
        temp_zone_file.write(f"            3600        ; Refresh\n")
        temp_zone_file.write(f"            1800        ; Retry\n")
        temp_zone_file.write(f"            1209600     ; Expire\n")
        temp_zone_file.write(f"            86400 )     ; Negative Cache TTL\n")
        temp_zone_file.write(f";\n")
        temp_zone_file.write(f"@       IN  NS  ns1.a1b2c3d4e5.fr.\n")
        temp_zone_file.write(f"@       IN  NS  ns2.a1b2c3d4e5.fr.\n")
        temp_zone_file.write(f"@       IN  A   51.210.255.66\n")
        temp_zone_file.write(f"@       IN  AAAA  2001:41d0:304:200::5ec6\n")
        temp_zone_file.write(f"bo      IN  A   51.210.255.66\n")
        temp_zone_file.write(f"bo      IN  AAAA  2001:41d0:304:200::5ec6\n")

        # Move the temporary file to the Nginx config directory with elevated privileges
        run_command(f"mv {temp_zone_file_path} {zone_file_path}", elevated=True)

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
        if "The DNS response does not contain an answer to the question" in str(e):
            error_message = f"La configuration DNS pour {domain_name} est incorrecte. Si vous venez de configurer le DNS, attendez quelques heures et réessayez."
        socketio.emit("error", error_message)
        socketio.emit("console", f"Erreur lors de la vérification DNS pour {domain_name}: {str(e)}")
        return False