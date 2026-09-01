# Deploying StratMaster CS2

Two environments, deliberately separate:

| | Production | Staging |
|---|---|---|
| Where | AWS EC2 | the dev machine |
| URL | `https://stratmaster.fun` | `https://overarch-omega-referee.ngrok-free.dev` |
| Bot | `@StratMasterCS2_bot` (`8637718779`) | `@dev00000000bot` (`8600115438`) |
| Compose file | `docker-compose.prod.yml` | `docker-compose.yml` |
| TLS | nginx + Let's Encrypt | terminated by ngrok |
| Database | its own volume on the box | its own volume locally |

**The two bots must never share a token.** Telegram delivers each update to
whichever poller asks first, so one token running in both places would send
roughly half of every real player's messages to the test server.

---

## 1. Production — first deploy

### 1.1 The box

An `t3.small` (2 GB) is the realistic floor: Postgres, Redis, two uvicorn
workers, the bot and nginx all share it. `t3.micro` will run but swaps under
a frontend image build.

- Ubuntu 24.04 LTS, 20 GB gp3.
- **Allocate an Elastic IP and associate it.** Without one the public IP
  changes on every stop/start and the DNS records below silently go stale.
- Security group inbound: `22` from your IP only, `80` and `443` from
  anywhere. Nothing else — in particular not 5432 or 6379; the production
  compose file keeps both off the host on purpose.

```bash
ssh ubuntu@<ELASTIC_IP>

sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker ubuntu
exit           # log back in for the group to apply
```

### 1.2 DNS at nic.ua

In the `stratmaster.fun` DNS records, pointing at the Elastic IP:

| Type | Name | Value |
|---|---|---|
| A | `@` | `<ELASTIC_IP>` |
| A | `www` | `<ELASTIC_IP>` |

Wait for it to resolve before issuing a certificate — Let's Encrypt
validates over the public DNS, and a failed run counts against the rate
limit (5 per domain per week):

```bash
dig +short stratmaster.fun
```

### 1.3 Code and secrets

```bash
git clone https://github.com/4Dream-UA/StratMaster-CS2.git
cd StratMaster-CS2
cp .env.sample .env
nano .env
```

Production values that differ from the sample:

```ini
POSTGRES_PASSWORD=<long random string>
DATABASE_URL=postgresql+asyncpg://stratmaster:<same password>@db:5432/stratmaster_db
BOT_TOKEN=<the @StratMasterCS2_bot token>
WEBAPP_URL=https://stratmaster.fun
SECRET_KEY=<openssl rand -hex 32>
DEBUG=False
ENVIRONMENT=production
OPENAI_API_KEY=<your OpenAI key, or blank to disable the assistant>
```

`NGROK_*` stay blank in production — nothing there reads them.

### 1.4 Certificate

Issued before the stack starts, because nginx won't come up without one and
certbot needs port 80 free to prove the domain:

```bash
sudo docker run --rm -p 80:80 \
  -v stratmaster-cs2_certbot_conf:/etc/letsencrypt \
  -v stratmaster-cs2_certbot_www:/var/www/certbot \
  certbot/certbot certonly --standalone \
  -d stratmaster.fun -d www.stratmaster.fun \
  --email <your email> --agree-tos --no-eff-email
```

Volume names are `<project>_<volume>`; the project name is the directory
name lowercased. Confirm with `docker volume ls` if the paths look wrong.

### 1.5 Start

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
```

Migrations run automatically on backend start. Expect
`Running upgrade ... -> 0036_board_own_image` on the first boot, then
`Application startup complete`.

Check it end to end:

```bash
curl -I https://stratmaster.fun            # 200, and a valid certificate
curl -s https://stratmaster.fun/api/settings
```

### 1.6 Point Telegram at it

In [@BotFather](https://t.me/BotFather), for `@StratMasterCS2_bot`:

- `/setmenubutton` → the bot → `https://stratmaster.fun` → button label.
- `/setdomain` → the bot → `stratmaster.fun` (required for Telegram Login).

Then open the bot and check the Mini App loads over the real domain.

### 1.7 Make yourself an admin

The database starts empty apart from seeded maps, cases and forum
categories. Open the app once so your account is created the normal way,
then:

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U stratmaster -d stratmaster_db \
  -c "UPDATE users SET is_admin = true WHERE username = 'evgeniygost';"
```

---

## 2. Production — routine tasks

### Deploying a change

```bash
cd StratMaster-CS2
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Zero-config: migrations run on start, and the frontend image rebuilds with
new content hashes. `index.html` is served `no-cache`, so clients pick the
new bundle up on their next load rather than after a cache expiry.

### Backups

`scripts/backup_db.sh` dumps to `./backups`, keeps 14 days, and is safe to
run while live. Schedule it:

```bash
crontab -e
# 03:00 daily
0 3 * * * cd /home/ubuntu/StratMaster-CS2 && ./scripts/backup_db.sh >> backup.log 2>&1
```

`./scripts/restore_db.sh backups/stratmaster_<timestamp>.sql.gz` restores.
Uploaded images live in the `uploads_data` volume and are **not** in the
dump — copy them separately if that matters:

```bash
docker run --rm -v stratmaster-cs2_uploads_data:/u -v $(pwd):/out alpine \
  tar czf /out/uploads.tar.gz -C /u .
```

### Certificate renewal

The `certbot` service renews automatically. nginx keeps serving the old
certificate until it reloads, so reload it weekly:

```bash
crontab -e
0 4 * * 1 cd /home/ubuntu/StratMaster-CS2 && docker compose -f docker-compose.prod.yml exec -T frontend nginx -s reload
```

### Logs

```bash
docker compose -f docker-compose.prod.yml logs -f --tail=100 backend
```

Application errors are also written to the database and readable in the
admin panel under **Errors (24h)** — that catches frontend crashes too,
which never reach these logs.

---

## 3. Staging (ngrok)

Stays on the dev machine and keeps running the plain `docker-compose.yml`.
The only thing that changes is which bot it drives — its `.env` now holds
the **development** token, so testing can't touch real players:

```ini
BOT_TOKEN=8600115438:...            # @dev00000000bot
WEBAPP_URL=https://overarch-omega-referee.ngrok-free.dev/
NGROK_DOMAIN=overarch-omega-referee.ngrok-free.dev
```

The ngrok domain is reserved, so it survives restarts and doesn't need
reconfiguring. Bring it up with the tunnel:

```bash
docker compose --profile ngrok up -d
```

In BotFather, set `@dev00000000bot`'s menu button and domain to the ngrok
URL, exactly as in 1.6.

---

## 4. Things that will bite

**Uploads are a volume, not a directory.** In production nothing bind-mounts
the source tree, so `backend/uploads` only exists inside the container.
`uploads_data` is what keeps player and admin images across redeploys —
don't remove it with `docker compose down -v`.

**`docker compose down -v` deletes the database.** `-v` removes named
volumes, `postgres_data` included. Use plain `down`, or just `up -d --build`
to redeploy.

**Don't run the test suite against production.** `backend/tests/conftest.py`
points at `localhost:5433/stratmaster_test`, which only exists on the dev
machine — and the production compose doesn't publish 5433 at all.

**Ports 5432 and 6379 must stay closed.** The production compose keeps them
off the host; don't add them back "to check something" on a box with a
public IP.

**One bot token per environment.** Repeated because it is the mistake with
the worst symptoms: intermittent, silent, and it hits real users.
