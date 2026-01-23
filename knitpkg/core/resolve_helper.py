
def parse_project_name(name: str) -> tuple[str, str]:
    """Parse package name format @org/package-name into (org, pack_name) tuple."""
    if name.startswith('@') and '/' in name:
        parts = name[1:].split('/', 1)
        return parts[0], parts[1]
    return '', name    

def normalize_dep_name(name: str, organization: str) -> str:
    org, dep_name = parse_project_name(name)
    if org:
        return name
    return f"@{organization.lower()}/{dep_name.lower()}"
