#!/usr/bin/env python3
"""
Auth service for Caddy forward_auth.
Handles login, logout, session management, and user administration.
"""

import hashlib
import json
import os
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timedelta

# Configuration
PORT = 8000
DATA_FILE = os.path.join(os.path.dirname(__file__), "users.json")
SESSIONS_FILE = os.path.join(os.path.dirname(__file__), "sessions.json")
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

    def do_GET(self):
        path = urlparse(self.path).path
        user = self.get_current_user()
        users = load_users()

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
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
            form { margin: 20px 0; }
            input[type="text"], input[type="password"] { padding: 10px; margin: 5px 0; width: 100%; box-sizing: border-box; }
            button, input[type="submit"] { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; margin-top: 10px; }
            button:hover, input[type="submit"]:hover { background: #0056b3; }
            .error { color: red; margin: 10px 0; }
            .success { color: green; margin: 10px 0; }
            ul { list-style: none; padding: 0; }
            li { padding: 10px 0; border-bottom: 1px solid #eee; }
            .user-row { display: flex; justify-content: space-between; align-items: center; }
            nav { margin-bottom: 30px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
            nav a { margin-right: 15px; }
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
        users = load_users()
        is_admin = users.get(user, {}).get('role') == 'admin' if user else False

        html = f"""<!DOCTYPE html>
<html>
<head><title>doughughes.net</title>{self.base_style()}</head>
<body>
{self.nav(user)}
<h1>Apps</h1>
<ul>
<li><a href="/lottery">Lottery Numbers</a></li>
"""
        if user:
            html += '<li><a href="/random-word">Random Word</a></li>'
        else:
            html += '<li>Random Word <em>(login required)</em></li>'

        html += """
</ul>
</body>
</html>"""
        return html

    def login_page(self, error=None):
        error_html = f'<p class="error">{error}</p>' if error else ''
        return f"""<!DOCTYPE html>
<html>
<head><title>Login - doughughes.net</title>{self.base_style()}</head>
<body>
{self.nav(None)}
<h1>Login</h1>
{error_html}
<form method="POST" action="/login">
    <input type="text" name="username" placeholder="Username" required autofocus>
    <input type="password" name="password" placeholder="Password" required>
    <input type="submit" value="Login">
</form>
</body>
</html>"""

    def account_page(self, user, error=None, success=None):
        error_html = f'<p class="error">{error}</p>' if error else ''
        success_html = f'<p class="success">{success}</p>' if success else ''
        return f"""<!DOCTYPE html>
<html>
<head><title>Account - doughughes.net</title>{self.base_style()}</head>
<body>
{self.nav(user)}
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
<head><title>User Management - doughughes.net</title>{self.base_style()}</head>
<body>
{self.nav('admin')}
<h1>User Management</h1>
{error_html}{success_html}
<h2>Current Users</h2>
<ul>{user_list}</ul>
<h2>Add User</h2>
<form method="POST" action="/admin/users/add">
    <input type="text" name="username" placeholder="Username" required>
    <input type="password" name="password" placeholder="Password" required>
    <select name="role">
        <option value="user">User</option>
        <option value="admin">Admin</option>
    </select>
    <input type="submit" value="Add User">
</form>
</body>
</html>"""

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), AuthHandler)
    print(f"Auth service running on http://127.0.0.1:{PORT}")
    server.serve_forever()
