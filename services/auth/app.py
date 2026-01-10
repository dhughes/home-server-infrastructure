#!/usr/bin/env python3
"""
Auth service for Caddy forward_auth.
Handles login, logout, session management, and user administration.
Dynamically loads apps from ~/apps/*/app.json
"""

import glob
import hashlib
import json
import os
import re
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timedelta

# Configuration
PORT = 8000
DATA_FILE = os.path.join(os.path.dirname(__file__), "users.json")
SESSIONS_FILE = os.path.join(os.path.dirname(__file__), "sessions.json")

# Auto-detect apps directory (prod vs dev)
PROD_APPS_DIR = "/home/dhughes/apps"
DEV_APPS_DIR = "/Users/doughughes/Projects/Personal"
APPS_DIR = os.getenv("APPS_DIR", PROD_APPS_DIR if os.path.exists(PROD_APPS_DIR) else DEV_APPS_DIR)

SESSION_DURATION_DAYS = 30

# In-memory session store (loaded from file for persistence)
sessions = {}

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{hashed.hex()}"

def verify_password(password, stored):
    salt, _ = stored.split(':')
    return hash_password(password, salt) == stored

def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    # Create default admin user
    users = {"admin": {"password": hash_password("changeme"), "role": "admin"}}
    save_users(users)
    return users

def save_users(users):
    with open(DATA_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_sessions():
    global sessions
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, 'r') as f:
            sessions = json.load(f)
    # Clean expired sessions
    now = datetime.now().isoformat()
    sessions = {k: v for k, v in sessions.items() if v.get('expires', '') > now}

def save_sessions():
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(sessions, f, indent=2)

def create_session(username):
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(days=SESSION_DURATION_DAYS)).isoformat()
    sessions[token] = {"username": username, "expires": expires}
    save_sessions()
    return token

def get_session(token):
    if token in sessions:
        session = sessions[token]
        if session.get('expires', '') > datetime.now().isoformat():
            return session
        del sessions[token]
        save_sessions()
    return None

def delete_session(token):
    if token in sessions:
        del sessions[token]
        save_sessions()

def parse_caddy_conf(config_path):
    """
    Parse a caddy.conf file to extract routing metadata.

    Returns: dict with keys 'path', 'port', 'public'
    Returns None if parsing fails.
    """
    try:
        with open(config_path, 'r') as f:
            content = f.read()

        # Extract path from: handle /path* { or handle /path/* {
        path_match = re.search(r'handle\s+(/[^\s{]*)', content)
        if not path_match:
            return None

        path = path_match.group(1)
        # Remove trailing * if present
        path = re.sub(r'\*+$', '', path)

        # Extract port from: reverse_proxy localhost:PORT
        port_match = re.search(r'reverse_proxy\s+localhost:(\d+)', content)
        if not port_match:
            return None

        port = int(port_match.group(1))

        # Check if public (no auth)
        # Look for 'forward_auth' directive
        has_auth = bool(re.search(r'forward_auth', content))
        is_public = not has_auth

        return {
            'path': path,
            'port': port,
            'public': is_public
        }
    except (IOError, ValueError) as e:
        print(f"Warning: Could not parse {config_path}: {e}")
        return None

def parse_caddy_subdomain_conf(config_path):
    """
    Parse a caddy-subdomain.conf file to extract subdomain.

    Returns: subdomain string (e.g., 'cranium-charades.doughughes.net')
    Returns None if parsing fails.
    """
    try:
        with open(config_path, 'r') as f:
            content = f.read()

        # Extract subdomain from: subdomain.doughughes.net {
        subdomain_match = re.search(r'^([a-zA-Z0-9\-\.]+)\s*\{', content, re.MULTILINE)
        if not subdomain_match:
            return None

        return subdomain_match.group(1)
    except (IOError, ValueError) as e:
        print(f"Warning: Could not parse {config_path}: {e}")
        return None

def load_apps():
    """Load all app configurations from ~/apps/*/app.json and ~/apps/*/caddy.conf"""
    apps = []
    pattern = os.path.join(APPS_DIR, "*", "app.json")
    for config_path in glob.glob(pattern):
        try:
            # Load display data from app.json
            with open(config_path, 'r') as f:
                app = json.load(f)
                app['_config_path'] = config_path
                app['_app_dir'] = os.path.dirname(config_path)

            # Load routing data from caddy.conf
            caddy_conf_path = os.path.join(app['_app_dir'], 'caddy.conf')
            if os.path.exists(caddy_conf_path):
                routing_data = parse_caddy_conf(caddy_conf_path)
                if routing_data:
                    app.update(routing_data)
                else:
                    print(f"Warning: Could not parse caddy.conf for {app.get('name', 'Unknown')}")
                    continue
            else:
                # Backward compatibility: try to read from app.json
                if 'path' not in app or 'port' not in app:
                    print(f"Warning: No caddy.conf and incomplete app.json for {app['_app_dir']}")
                    continue

            # Check for subdomain config
            caddy_subdomain_path = os.path.join(app['_app_dir'], 'caddy-subdomain.conf')
            if os.path.exists(caddy_subdomain_path):
                subdomain = parse_caddy_subdomain_conf(caddy_subdomain_path)
                if subdomain:
                    app['subdomain'] = subdomain

            apps.append(app)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load {config_path}: {e}")

    # Sort by name
    apps.sort(key=lambda a: a.get('name', ''))
    return apps

# Load data on startup
load_sessions()

class AuthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging

    def get_cookie(self, name):
        if 'Cookie' in self.headers:
            cookie = SimpleCookie(self.headers['Cookie'])
            if name in cookie:
                return cookie[name].value
        return None

    def set_cookie(self, name, value, max_age=None):
        cookie = f"{name}={value}; Path=/; HttpOnly; SameSite=Lax"
        if max_age is not None:
            cookie += f"; Max-Age={max_age}"
        self.send_header('Set-Cookie', cookie)

    def get_current_user(self):
        token = self.get_cookie('session')
        if token:
            session = get_session(token)
            if session:
                return session['username']
        return None

    def send_html(self, html, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())

    def send_redirect(self, location):
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()

    def send_file(self, filepath, content_type):
        """Serve a static file"""
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except IOError:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        user = self.get_current_user()
        users = load_users()

        # Serve app images
        if path.startswith('/app-image/'):
            app_name = path[len('/app-image/'):]
            # Find the app and serve its image
            apps = load_apps()
            for app in apps:
                if os.path.basename(app['_app_dir']) == app_name:
                    image = app.get('image')
                    if image:
                        image_path = os.path.join(app['_app_dir'], image)
                        if os.path.exists(image_path):
                            ext = os.path.splitext(image)[1].lower()
                            content_types = {
                                '.png': 'image/png',
                                '.jpg': 'image/jpeg',
                                '.jpeg': 'image/jpeg',
                                '.gif': 'image/gif',
                                '.svg': 'image/svg+xml',
                                '.webp': 'image/webp'
                            }
                            content_type = content_types.get(ext, 'application/octet-stream')
                            self.send_file(image_path, content_type)
                            return
            self.send_response(404)
            self.end_headers()
            return

        if path == '/verify':
            # Caddy forward_auth endpoint
            if user:
                self.send_response(200)
                self.send_header('X-Auth-User', user)
                self.end_headers()
            else:
                self.send_response(401)
                self.end_headers()

        elif path == '/login':
            if user:
                self.send_redirect('/')
                return
            self.send_html(self.login_page())

        elif path == '/logout':
            token = self.get_cookie('session')
            if token:
                delete_session(token)
            self.send_response(302)
            self.set_cookie('session', '', max_age=0)
            self.send_header('Location', '/')
            self.end_headers()

        elif path == '/account':
            if not user:
                self.send_redirect('/login')
                return
            self.send_html(self.account_page(user))

        elif path == '/admin/users':
            if not user:
                self.send_redirect('/login')
                return
            if users.get(user, {}).get('role') != 'admin':
                self.send_html("<h1>Access Denied</h1><p>Admin only.</p>", 403)
                return
            self.send_html(self.admin_users_page(users))

        elif path == '/':
            self.send_html(self.index_page(user))

        else:
            self.send_html("<h1>404 Not Found</h1>", 404)

    def do_POST(self):
        path = urlparse(self.path).path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        params = parse_qs(body)

        user = self.get_current_user()
        users = load_users()

        if path == '/login':
            username = params.get('username', [''])[0]
            password = params.get('password', [''])[0]

            if username in users and verify_password(password, users[username]['password']):
                token = create_session(username)
                self.send_response(302)
                self.set_cookie('session', token, max_age=SESSION_DURATION_DAYS * 86400)
                self.send_header('Location', '/')
                self.end_headers()
            else:
                self.send_html(self.login_page(error="Invalid username or password"))

        elif path == '/account':
            if not user:
                self.send_redirect('/login')
                return

            current_password = params.get('current_password', [''])[0]
            new_password = params.get('new_password', [''])[0]
            confirm_password = params.get('confirm_password', [''])[0]

            if not verify_password(current_password, users[user]['password']):
                self.send_html(self.account_page(user, error="Current password is incorrect"))
            elif new_password != confirm_password:
                self.send_html(self.account_page(user, error="New passwords don't match"))
            elif len(new_password) < 8:
                self.send_html(self.account_page(user, error="Password must be at least 8 characters"))
            else:
                users[user]['password'] = hash_password(new_password)
                save_users(users)
                self.send_html(self.account_page(user, success="Password updated successfully"))

        elif path == '/admin/users/add':
            if not user or users.get(user, {}).get('role') != 'admin':
                self.send_html("<h1>Access Denied</h1>", 403)
                return

            username = params.get('username', [''])[0]
            password = params.get('password', [''])[0]
            role = params.get('role', ['user'])[0]

            if username in users:
                self.send_html(self.admin_users_page(users, error="User already exists"))
            elif len(username) < 3:
                self.send_html(self.admin_users_page(users, error="Username must be at least 3 characters"))
            elif len(password) < 8:
                self.send_html(self.admin_users_page(users, error="Password must be at least 8 characters"))
            else:
                users[username] = {"password": hash_password(password), "role": role}
                save_users(users)
                self.send_html(self.admin_users_page(users, success=f"User '{username}' added"))

        elif path == '/admin/users/delete':
            if not user or users.get(user, {}).get('role') != 'admin':
                self.send_html("<h1>Access Denied</h1>", 403)
                return

            username = params.get('username', [''])[0]
            if username == user:
                self.send_html(self.admin_users_page(users, error="Cannot delete yourself"))
            elif username in users:
                del users[username]
                save_users(users)
                self.send_html(self.admin_users_page(users, success=f"User '{username}' deleted"))
            else:
                self.send_html(self.admin_users_page(users, error="User not found"))

        else:
            self.send_html("<h1>404 Not Found</h1>", 404)

    def base_style(self):
        return """
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            h1 { color: #333; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
            form { margin: 20px 0; }
            input[type="text"], input[type="password"] {
                padding: 10px;
                margin: 5px 0;
                width: 100%;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            button, input[type="submit"] {
                padding: 10px 20px;
                background: #007bff;
                color: white;
                border: none;
                cursor: pointer;
                margin-top: 10px;
                border-radius: 4px;
            }
            button:hover, input[type="submit"]:hover { background: #0056b3; }
            .error { color: red; margin: 10px 0; }
            .success { color: green; margin: 10px 0; }
            ul { list-style: none; padding: 0; }
            li { padding: 10px 0; border-bottom: 1px solid #eee; }
            .user-row { display: flex; justify-content: space-between; align-items: center; }
            nav {
                margin-bottom: 30px;
                padding: 15px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            nav a { margin-right: 15px; }

            /* Card grid */
            .app-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            .app-card {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                transition: transform 0.2s, box-shadow 0.2s;
                text-decoration: none;
                color: inherit;
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
                position: relative;
            }
            .app-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 4px 16px rgba(0,0,0,0.15);
                text-decoration: none;
            }
            .app-card-lock {
                position: absolute;
                top: 12px;
                right: 12px;
                font-size: 24px;
                z-index: 10;
            }
            .app-card-image {
                width: 256px;
                height: 256px;
                border-radius: 16px;
                object-fit: cover;
                margin-bottom: 16px;
            }
            .app-card-icon {
                width: 256px;
                height: 256px;
                border-radius: 16px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 128px;
                margin-bottom: 16px;
                flex-shrink: 0;
                overflow: hidden;
            }
            .app-card-name {
                font-size: 18px;
                font-weight: 600;
                color: #333;
                margin-bottom: 4px;
            }
            .app-card-description {
                font-size: 14px;
                color: #666;
            }

            /* Forms container */
            .form-container {
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                max-width: 400px;
            }
        </style>
        """

    def nav(self, user):
        users = load_users()
        is_admin = users.get(user, {}).get('role') == 'admin' if user else False
        nav = '<nav><a href="/">Home</a>'
        if user:
            nav += '<a href="/account">Account</a>'
            if is_admin:
                nav += '<a href="/admin/users">Users</a>'
            nav += f'<a href="/logout">Logout ({user})</a>'
        else:
            nav += '<a href="/login">Login</a>'
        nav += '</nav>'
        return nav

    def index_page(self, user):
        apps = load_apps()

        cards_html = ""
        for app in apps:
            is_public = app.get('public', True)

            # Skip private apps for non-logged-in users (don't show at all)
            if not is_public and not user:
                continue

            name = app.get('name', 'Unnamed App')
            description = app.get('description', '')
            icon = app.get('icon', '📦')
            image = app.get('image')
            app_dir_name = os.path.basename(app['_app_dir'])

            # Prefer subdomain link if available, otherwise use path
            subdomain = app.get('subdomain')
            if subdomain:
                link = f"https://{subdomain}"
            else:
                link = app.get('path', '/')

            # Image or icon
            if image:
                image_html = f'<img src="/app-image/{app_dir_name}" class="app-card-image" alt="{name}">'
            else:
                image_html = f'<div class="app-card-icon">{icon}</div>'

            # Show lock icon for private apps when user is logged in
            lock_html = '<div class="app-card-lock">🔒</div>' if not is_public and user else ''

            cards_html += f'''
            <a href="{link}" class="app-card">
                {lock_html}
                {image_html}
                <div class="app-card-name">{name}</div>
                <div class="app-card-description">{description}</div>
            </a>
            '''

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>doughughes.net</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    {self.base_style()}
</head>
<body>
{self.nav(user)}
<h1>Apps</h1>
<div class="app-grid">
{cards_html}
</div>
</body>
</html>"""
        return html

    def login_page(self, error=None):
        error_html = f'<p class="error">{error}</p>' if error else ''
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Login - doughughes.net</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    {self.base_style()}
</head>
<body>
{self.nav(None)}
<div class="form-container">
<h1>Login</h1>
{error_html}
<form method="POST" action="/login">
    <input type="text" name="username" placeholder="Username" required autofocus>
    <input type="password" name="password" placeholder="Password" required>
    <input type="submit" value="Login">
</form>
</div>
</body>
</html>"""

    def account_page(self, user, error=None, success=None):
        error_html = f'<p class="error">{error}</p>' if error else ''
        success_html = f'<p class="success">{success}</p>' if success else ''
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Account - doughughes.net</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    {self.base_style()}
</head>
<body>
{self.nav(user)}
<div class="form-container">
<h1>Account Settings</h1>
<p>Logged in as: <strong>{user}</strong></p>
<h2>Change Password</h2>
{error_html}{success_html}
<form method="POST" action="/account">
    <input type="password" name="current_password" placeholder="Current Password" required>
    <input type="password" name="new_password" placeholder="New Password" required>
    <input type="password" name="confirm_password" placeholder="Confirm New Password" required>
    <input type="submit" value="Update Password">
</form>
</div>
</body>
</html>"""

    def admin_users_page(self, users, error=None, success=None):
        error_html = f'<p class="error">{error}</p>' if error else ''
        success_html = f'<p class="success">{success}</p>' if success else ''

        user_list = ""
        for username, data in users.items():
            role = data.get('role', 'user')
            user_list += f"""
            <li class="user-row">
                <span>{username} ({role})</span>
                <form method="POST" action="/admin/users/delete" style="display:inline; margin:0;">
                    <input type="hidden" name="username" value="{username}">
                    <button type="submit" onclick="return confirm('Delete {username}?')">Delete</button>
                </form>
            </li>"""

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>User Management - doughughes.net</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    {self.base_style()}
</head>
<body>
{self.nav('admin')}
<div class="form-container" style="max-width: 600px;">
<h1>User Management</h1>
{error_html}{success_html}
<h2>Current Users</h2>
<ul>{user_list}</ul>
<h2>Add User</h2>
<form method="POST" action="/admin/users/add">
    <input type="text" name="username" placeholder="Username" required>
    <input type="password" name="password" placeholder="Password" required>
    <select name="role" style="padding: 10px; width: 100%; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px;">
        <option value="user">User</option>
        <option value="admin">Admin</option>
    </select>
    <input type="submit" value="Add User">
</form>
</div>
</body>
</html>"""

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), AuthHandler)
    print(f"Auth service running on http://127.0.0.1:{PORT}")
    server.serve_forever()
