# Golf Planner — Hetzner Deployment

Deploys the FastAPI backend and Vite/React frontend as Docker containers on
**external host ports 5000 (API) and 5001 (app)** — chosen to avoid ports 3000
and 4000, which the existing app uses. A host Nginx reverse proxy fronts them on
two subdomains. Your existing application is not touched.

| Service  | Container port | Host port | Public hostname        |
|----------|----------------|-----------|------------------------|
| backend  | 8000           | 5000      | api.yourdomain.com     |
| frontend | 80             | 5001      | app.yourdomain.com     |

> Before you start: point DNS `A` records for `api.yourdomain.com` and
> `app.yourdomain.com` at the server's IP. Replace `yourdomain.com` everywhere
> below with your real domain.

---

## 1. SSH into the server

```bash
ssh root@YOUR_SERVER_IP
```

## 2. Clone the repo and check out the branch

```bash
cd /opt
git clone https://github.com/YOUR_ORG/SE4471GolfEventPlanner.git golf-planner
cd golf-planner
git checkout Caelan
```

## 3. Create the backend `.env` from the template

```bash
cp backend/.env.example backend/.env
nano backend/.env   # fill in real CLAUDE_API_KEY, MONGODB_URL, JWT_SECRET, SMTP_*, etc.
```

Set `FRONTEND_URL=https://app.yourdomain.com` so CORS allows the frontend.

> **Frontend API URL is baked at build time.** The frontend reads
> `VITE_API_URL` during `npm run build`, so export it before building (the
> compose file passes it through as a build arg):
> ```bash
> export VITE_API_URL=https://api.yourdomain.com
> ```

## 4. Build and start the containers

```bash
docker compose up -d --build
```

Check status and logs:

```bash
docker compose ps
docker compose logs -f backend     # first boot downloads the embedding model — give it a minute
```

Quick local smoke test (before Nginx/DNS):

```bash
curl http://127.0.0.1:5000/        # backend
curl -I http://127.0.0.1:5001/     # frontend
```

## 5. Add the Nginx reverse proxy and reload

```bash
sudo cp deploy/nginx-golf.conf /etc/nginx/sites-available/golf-planner
# Edit the file to replace yourdomain.com with your real domain:
sudo nano /etc/nginx/sites-available/golf-planner
sudo ln -s /etc/nginx/sites-available/golf-planner /etc/nginx/sites-enabled/

sudo nginx -t        # validate config (won't affect your existing app)
sudo systemctl reload nginx
```

## 6. Enable HTTPS with Certbot

```bash
sudo certbot --nginx -d api.yourdomain.com -d app.yourdomain.com
```

Certbot edits the server blocks in place — adding the `listen 443 ssl;` lines,
certificate paths, and an HTTP→HTTPS redirect. Reload happens automatically.

After issuing certs, confirm `FRONTEND_URL` (in `backend/.env`) and
`VITE_API_URL` use `https://`. If you changed `VITE_API_URL`, rebuild the
frontend so the new URL is baked in:

```bash
docker compose up -d --build frontend
```

---

## Updating after a code change

```bash
cd /opt/golf-planner
git pull
docker compose up -d --build
```

## Tearing it down (it's temporary)

```bash
docker compose down                       # stop containers
sudo rm /etc/nginx/sites-enabled/golf-planner && sudo systemctl reload nginx
```

## Notes

- **No MongoDB container** is deployed — `MONGODB_URL` must point at a reachable
  database (e.g. Atlas).
- **Weather features** rely on a separate MCP server (`127.0.0.1:8001`) that is
  not part of this stack; those features degrade gracefully with a "server not
  running" message. Everything else works without it.
