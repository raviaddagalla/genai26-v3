import whois

def check_domain_availability(domain: str):
    try:
        w = whois.whois(domain)

        # If creation_date exists → domain is registered
        if w.creation_date:
            return False  # Taken

        return True  # Available

    except Exception:
        # If WHOIS lookup fails, usually means domain is available
        return True
