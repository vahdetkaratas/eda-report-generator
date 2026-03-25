# VPS deployment roadmap — own domain

Step-by-step plan to run **EDA Report Generator** (Streamlit) on your VPS behind **Nginx** with **HTTPS** and your **domain**.

**Assumptions:** Ubuntu 22.04/24.04 LTS (adapt package names for Debian/other). You have root or `sudo`. App listens only on `127.0.0.1`; Nginx terminates TLS and proxies to Streamlit.

---

## Phase 0 — Decisions (before you touch the server)

| Decision | Recommendation |
|----------|------------------|
| **App user** | Dedicated Linux user `edaapp` (no root for the app process). |
| **Install path** | e.g. `/srv/eda-report-generator` or `/home/edaapp/app`. |
| **Python** | 3.10+ via `python3-venv` or `pyenv` (avoid relying on system `pip` globally). |
| **Domain** | e.g. `eda.example.com` (subdomain keeps main site separate). |
| **PDF export** | WeasyPrint needs extra OS libraries on Linux (see Phase 7). If you skip them, HTML still works. |

---

## Phase 1 — DNS

1. At your domain registrar / DNS host, create an **A record**:
   - **Name:** `eda` (or `@` if root domain)
   - **Value:** your VPS **public IPv4**
2. Optional: **AAAA** for IPv6 if your VPS has a stable v6 address.
3. Wait for propagation (often minutes; up to 48h in worst case). Check: `dig +short eda.example.com`

---

## Phase 2 — Server baseline

SSH in as root or sudo user.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ufw fail2ban unattended-upgrades
```

**Firewall (UFW):**

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

**Dedicated user:**

```bash
sudo adduser --disabled-password --gecos "" edaapp
sudo mkdir -p /srv/eda-report-generator
sudo chown edaapp:edaapp /srv/eda-report-generator
```

---

## Phase 3 — System packages (Python + Nginx + Certbot)

```bash
sudo apt install -y python3 python3-venv python3-pip git nginx certbot python3-certbot-nginx
```

---

## Phase 4 — Application install

As `edaapp` (use `sudo -u edaapp -i` or `su - edaapp`):

```bash
cd /srv/eda-report-generator
git clone https://github.com/YOUR_USER/7_eda_report_generator.git .
# or: scp/rsync from your machine instead of git
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-prod.txt
```

**Note:** Use **`requirements-prod.txt`** on the server (runtime only). For local development and tests, use `requirements-dev.txt` or `requirements.txt` (includes pytest).

**Demo data:** Ensure `data/demo_*` paths exist (they should be in the repo). Verify:

```bash
ls -la data/demo_customer/ data/demo_sales/
```

---

## Phase 5 — Streamlit production settings

Create config so Streamlit binds to localhost only and runs headless.

As `edaapp`, from project root:

```bash
mkdir -p .streamlit
```

**File:** `.streamlit/config.toml`

```toml
[server]
headless = true
address = "127.0.0.1"
port = 8501
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```

**Optional env (limits):** e.g. in systemd `Environment=` lines:

- `EDA_MAX_FILE_MB=50`
- `EDA_MAX_ROWS=500000`
- `EDA_SAMPLE_SIZE=50000`

---

## Phase 6 — systemd service (auto-start + restart)

Create **`/etc/systemd/system/eda-streamlit.service`** (adjust paths/user):

```ini
[Unit]
Description=EDA Report Generator (Streamlit)
After=network.target

[Service]
Type=simple
User=edaapp
Group=edaapp
WorkingDirectory=/srv/eda-report-generator
Environment="PATH=/srv/eda-report-generator/.venv/bin"
# Optional:
# Environment="EDA_MAX_FILE_MB=50"
ExecStart=/srv/eda-report-generator/.venv/bin/streamlit run src/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable eda-streamlit
sudo systemctl start eda-streamlit
sudo systemctl status eda-streamlit
```

Logs: `journalctl -u eda-streamlit -f`

---

## Phase 7 — Nginx reverse proxy + TLS (Let’s Encrypt)

**7.1** Server block (HTTP first — Certbot will add SSL).

Create **`/etc/nginx/sites-available/eda`** (replace `eda.example.com`):

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name eda.example.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    client_max_body_size 100M;
}
```

Enable site:

```bash
sudo ln -sf /etc/nginx/sites-available/eda /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**7.2** Obtain certificate:

```bash
sudo certbot --nginx -d eda.example.com
```

Follow prompts (email, agree). Certbot edits Nginx for HTTPS and renews via cron/systemd timer.

**7.3** Test renewal:

```bash
sudo certbot renew --dry-run
```

---

## Phase 8 — WeasyPrint (PDF) on the server (optional)

If **Download PDF** should work on the VPS, install OS deps (Debian/Ubuntu family):

```bash
sudo apt install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

Then restart the app:

```bash
sudo systemctl restart eda-streamlit
```

If PDF still fails, check logs: `journalctl -u eda-streamlit -n 100 --no-pager`

---

## Phase 9 — Security & operations checklist

- [ ] SSH: key-only login, `PasswordAuthentication no` (after keys work).
- [ ] `ufw` default deny incoming; only 22, 80, 443 as needed.
- [ ] App never listens on `0.0.0.0:8501` in production (only `127.0.0.1`).
- [ ] Keep system packages updated: `apt upgrade` regularly.
- [ ] Backups: snapshot VPS or backup `/srv/eda-report-generator` + `.streamlit` + systemd unit file.
- [ ] **Privacy:** The app includes an in-UI **Privacy & data handling** expander; ensure wording stays aligned with actual behavior after upgrades.

---

## Phase 10 — Deploy updates (routine)

```bash
sudo -u edaapp -i
cd /srv/eda-report-generator
source .venv/bin/activate
git pull
pip install -r requirements-prod.txt
exit
sudo systemctl restart eda-streamlit
```

---

## Quick reference

| Component | Role |
|-----------|------|
| **Streamlit** | App on `127.0.0.1:8501` |
| **Nginx** | HTTPS, proxy, `client_max_body_size` |
| **Certbot** | TLS certificates + auto-renewal |
| **systemd** | Process supervision |

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| 502 Bad Gateway | `systemctl status eda-streamlit`, `curl -I http://127.0.0.1:8501` |
| WebSocket / disconnect | Nginx `Upgrade` / `Connection` headers (see config above) |
| Upload too large | Raise `client_max_body_size` in Nginx and align `EDA_MAX_FILE_MB` |
| Permission errors (app user cannot read app dir / templates) | `chown -R edaapp:edaapp /srv/eda-report-generator` |

---

*This file is deployment documentation for maintainers; keep it in the repo or copy to your internal wiki.*
