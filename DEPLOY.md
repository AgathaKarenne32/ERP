# Deployment guide

This describes taking the MVP from `docker compose up` on a laptop to a small
production deployment on a single VPS. It is intentionally pragmatic — one host,
containers, Nginx/Caddy + Let's Encrypt — with notes on where to grow next.

---

## 1. Provision a VPS

Any of Hetzner / DigitalOcean / Contabo works. A 2 vCPU / 4 GB instance is
plenty for the MVP.

```bash
# As root, first login:
adduser deploy && usermod -aG sudo deploy      # non-root user
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy   # copy your key

# Firewall (ufw): allow SSH + HTTP/HTTPS only
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable

# Harden SSH (/etc/ssh/sshd_config): PermitRootLogin no, PasswordAuthentication no
systemctl restart ssh
```

Install Docker + Compose plugin:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker deploy
# log out/in so the group applies
```

---

## 2. Get the code & configure secrets

```bash
git clone <your-repo> app && cd app
cp .env.example .env
```

Edit `.env` for production — at minimum:

```env
POSTGRES_PASSWORD=<strong-random>
JWT_SECRET=<64+ char random>            # openssl rand -hex 48
CORS_ORIGINS=https://yourdomain.com
RUN_SEED=false                          # do NOT seed demo data in prod
ANTHROPIC_API_KEY=<your key>            # optional
```

**Secret management:** keep `.env` out of git (it already is). For anything
beyond a single host, use your platform's secret store (Docker/Swarm secrets,
SOPS + age, Doppler, Vault, or the cloud provider's secret manager) and inject
at deploy time rather than committing files.

---

## 3. Build & run the production stack

`docker-compose.prod.yml` builds the Angular app to static files served by Nginx
(which also proxies `/api`) and runs the backend with multiple uvicorn workers.

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f backend
```

For higher throughput you can switch the backend command to gunicorn with
uvicorn workers:

```yaml
command: ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker",
          "-w", "4", "-b", "0.0.0.0:8000"]
```

(Add `gunicorn` to `backend/pyproject.toml` dependencies.)

---

## 4. Domain + HTTPS (reverse proxy)

The `frontend` container already listens on `:80`. Put a TLS-terminating reverse
proxy in front. **Caddy** is the least-effort option (automatic Let's Encrypt):

```caddyfile
# /etc/caddy/Caddyfile
yourdomain.com {
    reverse_proxy localhost:80
}
```

Or **Nginx + Certbot** on the host:

```bash
sudo apt install nginx certbot python3-certbot-nginx
# server block proxy_pass http://localhost:80;  then:
sudo certbot --nginx -d yourdomain.com
```

Certificates auto-renew via the certbot systemd timer.

---

## 5. Database: managed vs. containerized

| | Containerized Postgres (this repo) | Managed Postgres (RDS / DO / Neon) |
| --- | --- | --- |
| Setup | Zero extra cost, in-compose | Provision + set `DATABASE_URL` |
| Backups | **Your responsibility** (below) | Automated, point-in-time |
| Ops (patching, failover) | Manual | Handled by provider |
| Best for | MVP / low traffic | Anything you can't afford to lose |

Recommendation: start containerized; move to managed before you have real
customer data.

**Backups (`pg_dump`), scheduled via cron:**

```bash
# /etc/cron.daily/pg-backup  (chmod +x)
docker compose -f /home/deploy/app/docker-compose.prod.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip \
  > /home/deploy/backups/ecommerce-$(date +\%F).sql.gz
find /home/deploy/backups -mtime +14 -delete    # keep 2 weeks
```

Store copies off-host (e.g. sync to S3/R2).

---

## 6. Migrations

The app bootstraps the schema on startup for convenience. In production prefer
running Alembic explicitly on deploy so schema changes are versioned:

```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

(Set `RUN_SEED=false` so startup doesn't seed demo data.)

---

## 7. CI/CD (suggested — GitHub Actions)

```
lint+test  →  build  →  deploy
```

- **Backend job:** `ruff check` + `black --check` + `pytest`.
- **Frontend job:** `npm ci` + `npm run build` + `npm test` (headless Chrome).
- **Build job:** build & push both Docker images to a registry (GHCR).
- **Deploy job:** SSH to the VPS, `docker compose -f docker-compose.prod.yml pull
  && up -d`, then `alembic upgrade head`.

Keep the SSH key and registry token in GitHub Actions secrets.

---

## 8. Observability (minimum)

- **Healthcheck:** `GET /api/health` returns `{"status":"ok"}` — wire it to your
  uptime monitor (UptimeRobot / BetterStack) and the container healthcheck.
- **Logs:** the backend logs are structured to stdout; ship them with
  `docker compose logs` or a driver (Loki, CloudWatch).
- **DB healthcheck** is already in compose (`pg_isready`).

---

## 9. Go-live checklist

- [ ] `.env` has strong `JWT_SECRET` and DB password; `RUN_SEED=false`.
- [ ] `CORS_ORIGINS` set to the real domain(s) only.
- [ ] HTTPS working; HTTP redirects to HTTPS.
- [ ] `ufw` allows only 22/80/443; root SSH + password auth disabled.
- [ ] `alembic upgrade head` run against the prod DB.
- [ ] Automated `pg_dump` backups verified (restore tested at least once).
- [ ] Healthcheck monitored; alerting configured.
- [ ] Anthropic key present (or chat intentionally in offline mode).
- [ ] Images/registry tags pinned (no `:latest` surprises).
