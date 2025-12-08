#!/usr/bin/env python3
"""
Generate Caddyfile from app.json configurations.
Reads ~/apps/*/app.json and generates caddy/Caddyfile
"""

import glob
import json
import os

APPS_DIR = "/home/dhughes/apps"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "caddy", "Caddyfile")

def load_apps():
    """Load all app configurations from ~/apps/*/app.json"""
    apps = []
    pattern = os.path.join(APPS_DIR, "*", "app.json")
    for config_path in glob.glob(pattern):
        try:
            with open(config_path, 'r') as f:
                app = json.load(f)
                apps.append(app)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load {config_path}: {e}")
    return apps

def generate_caddyfile(apps):
    """Generate Caddyfile content from app configs"""
    lines = ["doughughes.net, www.doughughes.net {"]

    for app in apps:
        path = app.get('path', '')
        port = app.get('port')
        is_public = app.get('public', True)
        name = app.get('name', 'Unknown')

        if not path or not port:
            print(f"Warning: Skipping {name} - missing path or port")
            continue

        lines.append(f"\n\t# {name}")
        lines.append(f"\thandle {path}* {{")

        if not is_public:
            lines.append("\t\tforward_auth localhost:8000 {")
            lines.append("\t\t\turi /verify")
            lines.append("\t\t}")

        lines.append(f"\t\treverse_proxy localhost:{port}")
        lines.append("\t}")

    # Auth service handles everything else
    lines.append("""
\t# Auth service handles: /, /login, /logout, /account, /admin/*, /app-image/*
\thandle {
\t\treverse_proxy localhost:8000
\t}
}""")

    return "\n".join(lines)

def main():
    apps = load_apps()
    print(f"Found {len(apps)} apps")

    for app in apps:
        status = "public" if app.get('public', True) else "private"
        print(f"  - {app.get('name')}: {app.get('path')} -> port {app.get('port')} ({status})")

    caddyfile = generate_caddyfile(apps)

    with open(OUTPUT_FILE, 'w') as f:
        f.write(caddyfile)

    print(f"\nGenerated {OUTPUT_FILE}")
    print("\nRun 'sudo ./deploy.sh caddy' to apply changes")

if __name__ == '__main__':
    main()
