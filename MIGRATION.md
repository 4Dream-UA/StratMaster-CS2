# Moving production to another AWS account

Rebuilds the production box on a new account and carries the live data
across: the database, uploaded images, the TLS certificate and `.env`.
The domain, the bot token and the CryptoPay webhook URL do **not** change,
so nothing outside AWS needs reconfiguring — only the DNS records at
nic.ua, which move to the new Elastic IP.

Read [DEPLOY.md](DEPLOY.md) first if the current box is unfamiliar; this
document only covers the move.

**The single rule that matters:** the bot must never run on both boxes at
once. Telegram hands each update to whichever poller asks first, so two
pollers on one token silently split real players' messages between a live
server and a half-tested one. Every step below keeps exactly one running.

---

## What actually has to move

| What | Where it lives | How it travels |
|---|---|---|
| Database | `stratmaster-cs2_postgres_data` volume | `pg_dump` → gzip file |
| Uploaded images | `stratmaster-cs2_uploads_data` volume | `tar` of the volume |
| TLS certificate | `stratmaster-cs2_certbot_conf` volume | `tar` of the volume |
| Secrets | `~/StratMaster-CS2/.env` | copied as a file |
| Code | GitHub | `git clone` on the new box |

Carrying the certificate over is worth the extra step: the new box serves
HTTPS the moment it starts, the cutover doesn't wait on DNS propagation,
and no Let's Encrypt issuance is spent (5 per domain per week, and a failed
run counts).

Volume names are `<project>_<volume>`, where the project is the checkout
directory lowercased. Confirm with `docker volume ls` before trusting them.

---

## 1. On the new AWS account, before touching the old box

1. **Region.** Use the same one as today — `eu-central-1` (Frankfurt).
   Different region means different latency for the same players.
2. **Budget alarm.** Billing → Budgets → a monthly cost budget with an
   email alert. A new account is exactly where a surprise bill happens.
3. **Key pair.** EC2 → Key pairs → Create: RSA, `.pem`, named
   `stratmaster-prod`. It downloads once. On Windows, put it in
   `C:\Users\<you>\.ssh\` and lock it down — OpenSSH refuses a key that
   other users can read:

   ```powershell
   icacls "$env:USERPROFILE\.ssh\stratmaster-prod.pem" /inheritance:r /grant:r "$($env:USERNAME):R"
   ```

The old account's key does **not** work on the new box, and vice versa.

---

## 2. Take everything off the old box

On the old server. Nothing here stops the service — it stays live.

```bash
cd ~/StratMaster-CS2
export COMPOSE_FILE=docker-compose.prod.yml

# Database
./scripts/backup_db.sh                       # writes ./backups/stratmaster_<ts>.sql.gz

# Uploaded images and the certificate
docker run --rm -v stratmaster-cs2_uploads_data:/v -v $(pwd):/out alpine \
  tar czf /out/uploads.tar.gz -C /v .
docker run --rm -v stratmaster-cs2_certbot_conf:/v -v $(pwd):/out alpine \
  tar czf /out/letsencrypt.tar.gz -C /v .

ls -lh uploads.tar.gz letsencrypt.tar.gz backups/ | tail -5
```

Pull them to your own machine (PowerShell, from any directory):

```powershell
scp -i $env:USERPROFILE\.ssh\<old-key>.pem ubuntu@<OLD_IP>:~/StratMaster-CS2/uploads.tar.gz .
scp -i $env:USERPROFILE\.ssh\<old-key>.pem ubuntu@<OLD_IP>:~/StratMaster-CS2/letsencrypt.tar.gz .
scp -i $env:USERPROFILE\.ssh\<old-key>.pem ubuntu@<OLD_IP>:~/StratMaster-CS2/backups/stratmaster_*.sql.gz .
scp -i $env:USERPROFILE\.ssh\<old-key>.pem ubuntu@<OLD_IP>:~/StratMaster-CS2/.env .
```

`.env` is secrets — keep it out of the repo (it is gitignored) and delete
the local copy once the move is done.

---

## 3. Create the new box

EC2 → Instances → Launch an instance:

- **Name:** `stratmaster-prod`
- **AMI:** Ubuntu Server 24.04 LTS (64-bit x86)
- **Type:** `t3.small`. Postgres, Redis, two uvicorn workers, the bot and
  nginx share this box; `t3.micro` (1 GB) swaps hard during a frontend
  image build and the whole app crawls.
- **Key pair:** `stratmaster-prod` from step 1.
- **Network → security group**, create new, inbound only:

  | Type | Port | Source |
  |---|---|---|
  | SSH | 22 | My IP |
  | HTTP | 80 | Anywhere (0.0.0.0/0, ::/0) |
  | HTTPS | 443 | Anywhere |

  Nothing else. Not 5432, not 6379 — the production compose deliberately
  keeps both off the host.
- **Storage:** 20 GB gp3.

Then EC2 → Elastic IPs → **Allocate**, select it → Actions → **Associate**
→ the new instance. Without an Elastic IP the public address changes on
every stop/start and the DNS records go stale silently.

Install Docker:

```bash
ssh -i ~/.ssh/stratmaster-prod.pem ubuntu@<NEW_ELASTIC_IP>

sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker ubuntu
exit          # log back in for the group to take effect
```

---

## 4. Code and secrets on the new box

Upload `.env` and the three data files from your machine:

```powershell
scp -i $env:USERPROFILE\.ssh\stratmaster-prod.pem `
  .env uploads.tar.gz letsencrypt.tar.gz stratmaster_*.sql.gz `
  ubuntu@<NEW_ELASTIC_IP>:~/
```

Then on the new box:

```bash
git clone https://github.com/4Dream-UA/StratMaster-CS2.git
cd StratMaster-CS2
mv ~/.env .
mkdir -p backups && mv ~/stratmaster_*.sql.gz backups/
export COMPOSE_FILE=docker-compose.prod.yml
```

`.env` carries over unchanged — same domain, same bot, same keys. Worth
re-reading once:

```bash
grep -E 'WEBAPP_URL|ENVIRONMENT|DEBUG' .env
# WEBAPP_URL=https://stratmaster.fun
# DEBUG=False
# ENVIRONMENT=production
```

---

## 5. Restore the data

Volumes have to exist before anything can be unpacked into them, and the
database has to be running before a dump can go in. **Without the bot** —
the old one is still live and holds the token:

```bash
docker compose up -d --build db redis
docker compose ps        # wait until db is (healthy)
```

Images and certificate into their volumes:

```bash
docker run --rm -v stratmaster-cs2_uploads_data:/v -v ~:/in alpine \
  tar xzf /in/uploads.tar.gz -C /v
docker run --rm -v stratmaster-cs2_certbot_conf:/v -v ~:/in alpine \
  tar xzf /in/letsencrypt.tar.gz -C /v

docker run --rm -v stratmaster-cs2_certbot_conf:/v alpine \
  ls /v/live/stratmaster.fun        # fullchain.pem, privkey.pem must be here
```

Database:

```bash
FORCE=1 ./scripts/restore_db.sh backups/stratmaster_<timestamp>.sql.gz
```

Then the rest of the stack, still without the bot:

```bash
docker compose up -d --build backend frontend certbot
docker compose logs -f backend      # "Application startup complete"
```

Migrations run on backend start, so a dump from an older schema is brought
up to date automatically.

---

## 6. Test before touching DNS

The domain still points at the old box, so ask curl to use the new IP for
this one request. The copied certificate makes this a real HTTPS check,
not an insecure one:

```bash
curl -I --resolve stratmaster.fun:443:<NEW_ELASTIC_IP> https://stratmaster.fun
curl -s --resolve stratmaster.fun:443:<NEW_ELASTIC_IP> https://stratmaster.fun/api/settings
curl -I --resolve stratmaster.fun:443:<NEW_ELASTIC_IP> https://stratmaster.fun/uploads/<some-known-image>
```

Expect `200` and a valid certificate on all three. Row counts should match
the old box:

```bash
docker compose exec -T db psql -U stratmaster -d stratmaster_db \
  -c "SELECT (SELECT count(*) FROM users) users, (SELECT count(*) FROM strategies) strategies;"
```

If anything is off, fix it now — the old server is still serving players.

---

## 7. Cutover

Roughly five minutes of downtime, most of it DNS.

1. **Lower the TTL** on the `@` and `www` A records at nic.ua to 300
   seconds. Ideally an hour or more before the cutover, so the old TTL has
   expired everywhere by the time the change lands.

2. **Stop the old box** (on the old server). This is the moment the bot
   frees the token:

   ```bash
   cd ~/StratMaster-CS2 && docker compose -f docker-compose.prod.yml down
   ```

3. **Final dump from the old box** — everything players did since step 2.
   Postgres is stopped, so bring just it back up for the dump:

   ```bash
   docker compose -f docker-compose.prod.yml up -d db
   COMPOSE_FILE=docker-compose.prod.yml ./scripts/backup_db.sh
   docker compose -f docker-compose.prod.yml down
   ```

   Copy the new dump (and, if images were uploaded meanwhile, a fresh
   `uploads.tar.gz`) to the new box, then restore over the top exactly as
   in step 5. The dump is `--clean --if-exists`, so it replaces rather
   than merges.

4. **Switch DNS** at nic.ua:

   | Type | Name | Value |
   |---|---|---|
   | A | `@` | `<NEW_ELASTIC_IP>` |
   | A | `www` | `<NEW_ELASTIC_IP>` |

   Wait for it:

   ```bash
   dig +short stratmaster.fun          # must return the new IP
   ```

5. **Start everything on the new box, bot included:**

   ```bash
   cd ~/StratMaster-CS2
   docker compose -f docker-compose.prod.yml up -d --build
   docker compose -f docker-compose.prod.yml ps      # all Up
   ```

---

## 8. Verify

```bash
curl -I https://stratmaster.fun                       # 200, valid cert
curl -s https://stratmaster.fun/api/settings
curl -I https://stratmaster.fun/api/webhooks/cryptopay  # 401 — endpoint alive, rejects unsigned
```

Then by hand:

- Open the Mini App from the bot. It should load over `stratmaster.fun`.
- Log in as yourself — the account, balance, premium and inventory are all
  from the restored dump.
- Open a strategy with images: uploads came across if they render.
- Admin panel → Errors (24h) should be empty apart from anything you
  triggered on purpose.
- Send the bot `/start` — a reply proves exactly one poller holds the
  token.

Nothing changes in BotFather or CryptoPay: the domain is the same, so the
menu button, `/setdomain` and the webhook URL all still point at the right
place.

---

## 9. Cron on the new box

These do not travel with the data — they live in the old box's crontab.

```bash
crontab -e
```

```cron
# Nightly database backup, 14 days of history
0 3 * * * cd /home/ubuntu/StratMaster-CS2 && COMPOSE_FILE=docker-compose.prod.yml ./scripts/backup_db.sh >> backup.log 2>&1

# Weekly nginx reload, so renewed certificates are actually served
0 4 * * 1 cd /home/ubuntu/StratMaster-CS2 && docker compose -f docker-compose.prod.yml exec -T frontend nginx -s reload
```

The certificate renews itself in the `certbot` container; it just can't
signal nginx across containers, hence the reload.

---

## 10. Shut the old account down

Only once the new box has served real traffic for a day or two — a
terminated instance and a released Elastic IP are not recoverable.

1. Keep a copy of the last dump, `uploads.tar.gz` and `.env` somewhere off
   both servers.
2. EC2 → Instances → the old one → Instance state → **Terminate**.
3. EC2 → Elastic IPs → the old address → **Release**. An Elastic IP that
   isn't attached to a running instance is billed by the hour.
4. EC2 → Volumes and Snapshots: delete anything left behind. Terminating
   an instance doesn't always take its volumes.
5. Billing → check next month's forecast is zero before closing the
   account.

---

## What goes wrong

**Two bots on one token.** The symptom is that roughly half of every
player's messages get no answer, and it never appears in either box's
logs. Only one box may run the `bot` service; the steps above start the
new stack without it until the old one is down.

**`docker compose down -v` deletes the database.** `-v` removes named
volumes, `postgres_data` included. Plain `down` is what step 7 uses.

**Uploads are a volume, not a directory.** In production nothing
bind-mounts the source tree, so `backend/uploads` exists only inside the
container. A migration that forgets `uploads_data` loses every image ever
uploaded while the database still references them.

**The scripts default to the dev compose file.** `backup_db.sh` and
`restore_db.sh` call plain `docker compose`; on the production box export
`COMPOSE_FILE=docker-compose.prod.yml` first, as every snippet here does.

**No Elastic IP.** Restarting the instance then changes the public IP, and
the site goes down the next time the box stops — with DNS records that
look perfectly correct.
