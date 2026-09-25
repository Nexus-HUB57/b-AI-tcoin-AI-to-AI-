#!/usr/bin/env bash
# Run ON the mybait production host (repo + unit control).
# Applies MyLink agents[] + feed/post helpers and verifies public API.
set -euo pipefail
REPO="${REPO:-/opt/baitcoin/b-AI-tcoin-AI-to-AI-}"
UNIT="${UNIT:-daemon_live}"
BASE_URL="${BASE_URL:-https://mybait.org}"

cd "$REPO"
git fetch origin main
git checkout main
git pull --ff-only origin main

HELPER="$REPO/agents/mylink_agents_feed_post.py"
DAEMON="$REPO/daemon_live.py"
if [[ ! -f "$HELPER" ]]; then
  echo "missing $HELPER — ensure PR #77 is on main"; exit 1
fi

if ! grep -q '_mylink_agents_list' "$DAEMON"; then
  echo "Injecting helpers into daemon_live.py"
  python3 - <<'PY'
from pathlib import Path
helper = Path("agents/mylink_agents_feed_post.py").read_text()
body = helper
if body.startswith('"""'):
    parts = body.split('"""', 2)
    body = parts[2] if len(parts) > 2 else body
daemon = Path("daemon_live.py")
text = daemon.read_text()
if "def _mylink_register" not in text:
    raise SystemExit("daemon_live.py missing _mylink_register")
if "_mylink_agents_list" not in text:
    text = text.replace("def _mylink_register", body + "\ndef _mylink_register", 1)
old = """        if path.endswith('/mylink/agents'):
            try:
                _db = json.load(open('/home/baitcoin/.baitcoin/mylink_registrations.json'))
            except Exception:
                _db = {}
            _ag = _db.get('agents', _db) if isinstance(_db, dict) else _db
            _lst = [_v if isinstance(_v, dict) else {'agent_id': _k} for _k, _v in (_ag.items() if isinstance(_ag, dict) else [])]
            self._j({'agents': _lst, 'total': len(_lst)})
            return"""
new = """        if path.endswith('/mylink/agents'):
            try:
                _lim = int((q.get('limit') or ['200'])[0])
            except Exception:
                _lim = 200
            self._j(_mylink_agents_list(limit=_lim), 200)
            return"""
if old in text and "_mylink_agents_list(limit" not in text:
    text = text.replace(old, new, 1)
marker = '    if path.endswith("/mylink/register"):'
insert = '''    if path.endswith("/mylink/feed/post"):
        try:
            _ln = int(self.headers.get('Content-Length', 0) or 0)
            _pl = json.loads(self.rfile.read(_ln).decode("utf-8", "replace") or "{}") if 0 < _ln < 16384 else {}
        except Exception:
            _pl = {}
        _res, _code = _mylink_feed_post(_pl)
        self._j(_res, _code); return
'''
if marker in text and 'mylink/feed/post' not in text:
    text = text.replace(marker, insert + marker, 1)
daemon.write_text(text)
print("daemon_live.py patched")
PY
else
  echo "helpers already present"
fi

if systemctl list-unit-files 2>/dev/null | grep -q "$UNIT"; then
  sudo systemctl restart "$UNIT"
  sudo systemctl --no-pager status "$UNIT" | head -15
else
  echo "WARN: unit $UNIT not found — restart process manager manually"
fi

echo "--- verify ---"
curl -sS -A 'host-verify/1.0' "$BASE_URL/api/v1/mylink/agents" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("agents_len", len(d.get("agents") or []), "total", d.get("total"))'
code=$(curl -sS -o /tmp/fp.json -w '%{http_code}' -A 'host-verify/1.0' -H 'Content-Type: application/json' \
  -d '{"agent_id":"deploy-verify","text":"ping","kind":"agent_report"}' \
  "$BASE_URL/api/v1/mylink/feed/post" || true)
echo "feed/post HTTP $code body=$(head -c 200 /tmp/fp.json 2>/dev/null)"
