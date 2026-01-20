import os
import random


def _build_proxy(url: str) -> dict[str, str]:
    """Build a requests-compatible proxies dict from a single proxy URL.

    The same proxy is applied for both HTTP and HTTPS requests. The URL can
    optionally include basic auth credentials (e.g. http://user:pass@host:port).
    """
    return {
        "http": url,
        "https": url,
    }


def get_proxy() -> dict | None:
    """
    Return a proxy configuration for requests if environment variables are set.

    Supported env vars (in order of precedence):
      - PROXY_URLS: Comma-separated list of full proxy URLs. A random one is chosen.
      - PROXY_URL: Single full proxy URL.
      - PROXY_HOST/PROXY_PORT with optional PROXY_USERNAME/PROXY_PASSWORD

    Examples:
      PROXY_URLS="http://user:pass@proxy1.example.com:80, http://user:pass@proxy2.example.com:8080"
      PROXY_URL="http://user:pass@proxy1.example.com:80"
      PROXY_HOST="proxy1.example.com" PROXY_PORT="80" PROXY_USERNAME="user" PROXY_PASSWORD="pass"

    Returns None if no proxy configuration is present.
    """
    urls = os.getenv("PROXY_URLS")
    if urls:
        candidates = [u.strip() for u in urls.split(",") if u.strip()]
        if candidates:
            return _build_proxy(random.choice(candidates))

    url = os.getenv("PROXY_URL")
    if url:
        return _build_proxy(url)

    host = os.getenv("PROXY_HOST")
    port = os.getenv("PROXY_PORT")
    if host and port:
        user = os.getenv("PROXY_USERNAME")
        pwd = os.getenv("PROXY_PASSWORD")
        if user and pwd:
            auth = f"{user}:{pwd}@"
        else:
            auth = ""
        # Use http scheme for CONNECT proxies
        return _build_proxy(f"http://{auth}{host}:{port}")

    return None
