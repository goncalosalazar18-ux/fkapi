import random

def get_proxy() -> dict:
    """
    Returns the Webshare proxy configuration
    """
    proxy = "p.webshare.io:80"
    username = "gjxexemi-rotate"
    password = "4ca9ukvy4h48"
    
    proxy_formatted = {
        'http': f'http://{username}:{password}@{proxy}',
        'https': f'http://{username}:{password}@{proxy}'
    }
    return proxy_formatted
