import random

PROXY_LIST = [f"p.webshare.io:100{str(i).zfill(2)}" for i in range(100)]


def get_proxy() -> dict:
    """
    Returns a random proxy from the PROXY_LIST
    """
    proxy = random.choice(PROXY_LIST)
    proxy_formatted = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}',
    }
    
    return proxy_formatted
