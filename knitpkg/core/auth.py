import keyring
import hashlib
import platform
import socket
import uuid
import os
import httpx
import typer
from knitpkg.core.global_config import get_registry_url

CREDENTIALS_SERVICE = "knitpkg-mt"  # Name for keyring
SUPPORTED_PROVIDERS = ['github', 'gitlab', 'mql5forge', 'bitbucket']

def session_access_token():
    for p in SUPPORTED_PROVIDERS:
        try:
            access_token = keyring.get_password(CREDENTIALS_SERVICE, p)
            if access_token:
                return p, access_token
        except Exception:
            ...
    return None, None


def generate_device_fingerprint() -> str:
    """
    Generate unique device fingerprint.

    Combines:
    - Hostname
    - MAC address
    - OS username
    - Platform
    """
    hostname = socket.gethostname()
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8*6, 8)][::-1])
    username = os.getlogin()
    system = platform.system()

    fingerprint = f"{hostname}:{mac}:{username}:{system}"
    return hashlib.sha256(fingerprint.encode()).hexdigest()


async def register_device_with_registry(token: str, console):
    """Register current device with registry after successful login."""
    device_id = generate_device_fingerprint()
    device_name = f"{platform.node()} ({platform.system()})"

    registry_url = get_registry_url()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{registry_url}/auth/register-device",
            json={
                "device_id": device_id,
                "device_name": device_name,
                "device_type": detect_device_type()  # "laptop", "desktop", "ci"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

    if response.status_code == 403:
        data = response.json()
        console.print(f"\n[red]✗[/red] [bold]Device limit exceeded[/bold]")
        console.print(f"   Active devices: [yellow]{data['active_devices']}/{data['max_devices']}[/yellow]")
        console.print(f"   Manage devices at: [link]https://knitpkg.com/account/devices[/link]\n")
        raise typer.Exit(code=1)

    if response.status_code == 201:
        console.print(f"[green]✓[/green] Device registered: [dim]{device_name}[/dim]")


def detect_device_type() -> str:
    """Detect if running in CI/CD or personal machine."""
    ci_indicators = ["CI", "CONTINUOUS_INTEGRATION", "GITHUB_ACTIONS", "GITLAB_CI"]
    if any(os.getenv(var) for var in ci_indicators):
        return "ci"

    if platform.system() == "Darwin":
        return "laptop" if "MacBook" in platform.node() else "desktop"

    return "desktop"

