"""Basit erişim katmanı — form-tabanlı giriş + imzalı çerez oturumu.

Amaç: public deploy'da (Render vb.) panoyu URL'i olan herkesten korumak. Gerçek HTTP
Basic Auth (tarayıcının stillenemez gri pop-up'ı) yerine STİLLENEBİLİR bir giriş sayfası
kullanılır; aynı korumayı verir ama markaya/temaya uyar.

Env ile KOŞULLU:
- `OEE_AUTH_PASS` tanımlı DEĞİLSE auth tamamen kapalıdır (yerel dev + testler etkilenmez).
- Tanımlıysa: tüm yollar (login/logout/health ve statik login varlıkları hariç) çereze bağlanır.
- `OEE_AUTH_USER` (varsayılan "admin"), `OEE_AUTH_SECRET` (yoksa paroladan türetilir).

Çerez değeri sabit bir HMAC token'ıdır (parola ele geçmeden taklit edilemez). Bu, "basit
erişim katmanı"dır — bankacılık değil; gerçek çok-kullanıcılı kimlik için ileride OAuth/SSO.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import urllib.parse

COOKIE = "oee_auth"
_PUBLIC = ("/login", "/logout", "/health")


def _pass() -> str:
    return os.environ.get("OEE_AUTH_PASS", "")


def _user() -> str:
    return os.environ.get("OEE_AUTH_USER", "admin")


def _secret() -> bytes:
    return (os.environ.get("OEE_AUTH_SECRET") or _pass() or "dev").encode()


def enabled() -> bool:
    """Auth yalnız OEE_AUTH_PASS tanımlıysa aktiftir."""
    return bool(_pass())


def make_token() -> str:
    return hmac.new(_secret(), b"oee-authed", hashlib.sha256).hexdigest()


def verify(token: str | None) -> bool:
    if not token:
        return False
    return hmac.compare_digest(token, make_token())


def check_credentials(username: str, password: str) -> bool:
    u = hmac.compare_digest(username or "", _user())
    p = hmac.compare_digest(password or "", _pass())
    return u and p


def is_public(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in _PUBLIC)


def parse_login_form(body: bytes) -> tuple[str, str]:
    """application/x-www-form-urlencoded gövdeyi stdlib ile çözer (python-multipart gerekmez)."""
    data = urllib.parse.parse_qs(body.decode("utf-8", "ignore"))
    return data.get("username", [""])[0], data.get("password", [""])[0]


def login_page(error: bool = False) -> str:
    """Tema/cyan ile uyumlu, kendi kendine yeten (inline CSS) premium giriş sayfası."""
    err = (
        '<p class="err">Kullanıcı adı veya parola hatalı.</p>' if error else ""
    )
    return f"""<!doctype html>
<html lang="tr"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>OEE Panosu — Giriş</title>
<style>
  :root {{ --bg:#070809; --bg-3:#11141a; --ink:#eef2f6; --muted:#9099a8; --faint:#626c7a;
    --line:rgba(255,255,255,.10); --accent:#22d3ee; --accent-ink:#04232b; --loss:#fb7185;
    --ease:cubic-bezier(.32,.72,0,1); }}
  * {{ box-sizing:border-box; }}
  html {{ color-scheme:dark; }}
  body {{ margin:0; min-height:100dvh; display:grid; place-items:center; padding:1.5rem;
    font-family:"Plus Jakarta Sans",system-ui,sans-serif; background:var(--bg); color:var(--ink);
    -webkit-font-smoothing:antialiased; letter-spacing:-.01em; }}
  .aurora {{ position:fixed; inset:0; z-index:-1; pointer-events:none;
    background:
      radial-gradient(46rem 30rem at 12% -10%, rgba(34,211,238,.10), transparent 60%),
      radial-gradient(38rem 28rem at 108% 8%, rgba(167,139,250,.07), transparent 60%),
      radial-gradient(52rem 40rem at 50% 120%, rgba(52,211,153,.05), transparent 60%); }}
  .card {{ width:100%; max-width:380px; background:rgba(255,255,255,.022);
    border:1px solid var(--line); border-radius:22px; padding:6px;
    box-shadow:0 30px 70px -34px rgba(0,0,0,.85); }}
  .core {{ background:linear-gradient(180deg,rgba(255,255,255,.02),rgba(0,0,0,.14)),var(--bg-3);
    border-radius:16px; padding:1.8rem 1.6rem; box-shadow:inset 0 1px 0 rgba(255,255,255,.06); }}
  .brand {{ font-size:13px; font-weight:800; letter-spacing:.18em; color:var(--accent); }}
  .eyebrow {{ display:block; font-size:10px; font-weight:600; letter-spacing:.24em;
    text-transform:uppercase; color:var(--faint); margin:1.1rem 0 .25rem; }}
  h1 {{ font-size:1.35rem; font-weight:700; margin:0 0 1.4rem; letter-spacing:-.025em; }}
  label {{ display:block; font-size:10px; letter-spacing:.12em; text-transform:uppercase;
    color:var(--muted); margin:0 0 6px; }}
  input {{ width:100%; background:var(--bg); color:var(--ink); border:1px solid var(--line);
    border-radius:11px; padding:11px 12px; font:inherit; font-size:.9rem; margin-bottom:1rem;
    transition:border-color .3s var(--ease), box-shadow .3s var(--ease); }}
  input:focus {{ outline:none; border-color:var(--accent); box-shadow:0 0 0 3px rgba(34,211,238,.16); }}
  button {{ width:100%; margin-top:.3rem; font:inherit; font-weight:700; font-size:.9rem;
    cursor:pointer; border:1px solid transparent; border-radius:999px; padding:11px 18px;
    background:var(--accent); color:var(--accent-ink);
    transition:transform .3s var(--ease), filter .3s var(--ease); }}
  button:hover {{ filter:brightness(1.07); }}
  button:active {{ transform:translateY(1px) scale(.99); }}
  button:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
  .err {{ color:var(--loss); font-size:.8rem; margin:0 0 1rem; }}
  .foot {{ color:var(--faint); font-size:.72rem; margin:1.2rem 0 0; line-height:1.5; }}
</style></head>
<body>
  <div class="aurora"></div>
  <main class="card"><div class="core">
    <span class="brand">OEE</span>
    <span class="eyebrow">Üretim Verimliliği</span>
    <h1>Panoya Giriş</h1>
    {err}
    <form method="post" action="/login">
      <label for="u">Kullanıcı adı</label>
      <input id="u" name="username" autocomplete="username" autofocus required/>
      <label for="p">Parola</label>
      <input id="p" name="password" type="password" autocomplete="current-password" required/>
      <button type="submit">Giriş</button>
    </form>
    <p class="foot">Bu pano erişime kapalıdır. Giriş bilgisi için yöneticinize başvurun.</p>
  </div></main>
</body></html>"""
