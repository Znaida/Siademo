import os


def get_redis():
    """
    Retorna un cliente Upstash Redis usando REST API (compatible con Azure F1 — sin conexiones persistentes).
    Retorna None si las variables de entorno no están configuradas (entorno local sin Redis).
    """
    url = os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        return None
    try:
        from upstash_redis import Redis
        return Redis(url=url, token=token)
    except Exception:
        return None
