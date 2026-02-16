from typing import List
from pathlib import Path

from knitpkg.core.dependency_downloader import ProjectNode, ProjectNodeStatus
from knitpkg.core.console import Console
from knitpkg.core.global_config import is_global_telemetry, get_registry_url
from knitpkg.core.config import ProjectConfig
from knitpkg.core.registry import Registry

def _telemetry_enabled(project_dir: Path):
    if is_global_telemetry():
        return True
    
    return ProjectConfig(project_dir).get("telemetry", False)

def print_telemetry_warning(project_dir: Path):
    if _telemetry_enabled(project_dir):
        return
    
    from rich.console import Console
    console = Console(log_path=False)
    console.print(
        "\n[yellow bold]Telemetry remains disabled[/]. Please consider enabling it. "
        "The KnitPkg ecosystem's vitality depends on community participation. "
        "Enable telemetry with [cyan]`kp telemetry on`[/] to sustain this critical infrastructure."
    )

def send_telemetry_data(root_node: ProjectNode, project_dir: Path):
    """Send telemetry data about the project's dependencies."""
    if not _telemetry_enabled(project_dir):
        return
    
    if not root_node:
        return

    installed_nodes: List[ProjectNode] = [n for n in root_node.resolved_nodes(True) \
                                          if n.id is not None and n.status == ProjectNodeStatus.INSTALLED]
    if not installed_nodes:
        return
    
    registry: Registry = Registry(get_registry_url(), None, False)
    registry.record_install([n.id for n in installed_nodes], # type: ignore
                            [n.version for n in installed_nodes]) 
