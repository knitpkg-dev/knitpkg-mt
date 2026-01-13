import keyring

CREDENTIALS_SERVICE = "knitpkg-mt"  # Name for keyring
SUPPORTED_PROVIDERS = ['github', 'gitlab', 'mql5forge', 'bitbucket']

def session_provider():
    for p in SUPPORTED_PROVIDERS:
        try:
            if keyring.get_password(CREDENTIALS_SERVICE, p): # Check if token exists
                return p
        except Exception:
            ...
    return None

def session_access_token():
    for p in SUPPORTED_PROVIDERS:
        try:
            access_token = keyring.get_password(CREDENTIALS_SERVICE, p)
            if access_token:
                return p, access_token
        except Exception:
            ...
    return None, None
