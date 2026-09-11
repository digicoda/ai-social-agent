from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .auth import authenticate, create_admin, has_users
from .config import get_settings

DASHBOARD_DIR = Path(__file__).with_name("dashboard")


def _configured() -> bool:
    return bool(get_settings().session_secret)


def require_dashboard_session(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="dashboard login required")


def dashboard_login(request: Request, username: str, password: str) -> bool:
    settings = get_settings()
    if not _configured():
        return False
    if not has_users(settings.database_url):
        if not create_admin(settings.database_url, username, password):
            return False
    elif not authenticate(settings.database_url, username, password):
        return False
    request.session.clear()
    request.session["authenticated"] = True
    request.session["role"] = "admin"
    return True


def dashboard_signup(request: Request, username: str, password: str) -> bool:
    return dashboard_login(request, username, password)


def dashboard_logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/dashboard", status_code=303)


def dashboard_page(request: Request) -> HTMLResponse:
    path = DASHBOARD_DIR / "index.html"
    html = path.read_text(encoding="utf-8")
    settings = get_settings()
    account_exists = has_users(settings.database_url)

    html = html.replace("__AUTH_CONFIGURED__", "true" if _configured() else "false")
    html = html.replace("__HAS_ACCOUNT__", "true" if account_exists else "false")
    html = html.replace("__AUTHENTICATED__", "true" if request.session.get("authenticated") else "false")

    # Render the first-run choice in the HTML itself instead of relying on a
    # dynamically-created tab. This makes the signup option visible even when
    # a browser has cached the dashboard JavaScript.
    login_marker = '<div id="loginNotice" class="notice hidden"></div>'
    login_choices = '''
  <div id="authMode" style="display:flex;gap:8px;margin:18px 0 4px">
    <button type="button" id="signInTab" class="btn secondary" style="flex:1">Sign in</button>
    <button type="button" id="signUpTab" class="btn" style="flex:1">Create admin</button>
  </div>
'''
    if login_marker in html and 'id="authMode"' not in html:
        html = html.replace(login_marker, login_marker + login_choices)

    setup_script = r'''<script>
(function () {
  function initAuthMode() {
    const box = document.getElementById('login');
    const form = document.getElementById('loginForm');
    const signInTab = document.getElementById('signInTab');
    const signUpTab = document.getElementById('signUpTab');
    if (!box || !form || !signInTab || !signUpTab) return;

    const hasAccount = __HAS_ACCOUNT__;
    const heading = box.querySelector('h1');
    const subtitle = box.querySelector('p.muted');
    const button = form.querySelector('button');
    const notice = document.getElementById('loginNotice');
    let confirmationInput = document.getElementById('confirmPassword');
    let confirmationLabel = document.getElementById('confirmPasswordLabel');

    if (!confirmationInput) {
      confirmationLabel = document.createElement('label');
      confirmationLabel.id = 'confirmPasswordLabel';
      confirmationLabel.textContent = 'Confirm password';
      confirmationInput = document.createElement('input');
      confirmationInput.type = 'password';
      confirmationInput.id = 'confirmPassword';
      confirmationInput.autocomplete = 'new-password';
      confirmationInput.style.width = '100%';
      form.append(confirmationLabel, confirmationInput);
    }

    let signup = !hasAccount;

    function setMode(value, message) {
      signup = value;
      heading.textContent = value ? 'Create admin account' : 'Welcome back';
      subtitle.textContent = value
        ? 'First-time setup — create your administrator login.'
        : 'Sign in to your admin dashboard.';
      button.textContent = value ? 'Create account' : 'Sign in';
      signInTab.className = value ? 'btn secondary' : 'btn';
      signUpTab.className = value ? 'btn' : 'btn secondary';
      confirmationLabel.classList.toggle('hidden', !value);
      confirmationInput.classList.toggle('hidden', !value);
      confirmationInput.required = value;
      if (message) {
        notice.textContent = message;
        notice.classList.remove('hidden');
      } else {
        notice.classList.add('hidden');
      }
    }

    signInTab.onclick = function () { setMode(false, ''); };
    signUpTab.onclick = function () {
      setMode(true, 'Create your first admin account.');
    };

    form.onsubmit = async function (event) {
      event.preventDefault();
      const password = document.getElementById('password').value;
      if (signup && password !== confirmationInput.value) {
        setMode(true, 'Passwords do not match.');
        return;
      }
      if (signup && password.length < 8) {
        setMode(true, 'Password must be at least 8 characters.');
        return;
      }
      button.disabled = true;
      try {
        const response = await fetch('/dashboard/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: document.getElementById('username').value,
            password: password
          })
        });
        if (response.ok) {
          showApp();
          refresh();
        } else {
          const data = await response.json().catch(function () { return {}; });
          setMode(signup, data.detail || (signup ? 'Account could not be created.' : 'Invalid credentials.'));
        }
      } finally {
        button.disabled = false;
      }
    };

    setMode(signup, signup
      ? 'Welcome! Create your admin username and password to begin.'
      : '');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuthMode);
  } else {
    initAuthMode();
  }
})();
</script>'''
    html = html.replace('</body>', setup_script + '</body>')
    return HTMLResponse(html)
