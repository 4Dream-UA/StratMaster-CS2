# Standing production up again on a new AWS account

The previous production box is gone: its AWS account is suspended, so there
is no SSH to it and nothing can be copied off it. This is a clean deploy of
the same application on a new account, usually by someone other than the
owner, from their own machine and IP.

What that changes, compared with a planned move:

| | Planned move | This |
|---|---|---|
| Database | copied as a dump | restored from an off-server backup, or starts empty |
| Uploaded images | copied from the volume | gone unless a `uploads.tar.gz` survives elsewhere |
| TLS certificate | copied, no downtime | issued fresh — **DNS must point here first** |
| Secrets | copied from the old `.env` | handed over by the owner, some regenerated |
| Cutover | old box turned off first | nothing to turn off; the domain is already dark |

Read [DEPLOY.md](DEPLOY.md) for what the stack is made of. This document is
the sequence.

**Before anything else:** if the old account can still be reinstated (an
unpaid bill usually can be settled), do that first and take a dump — AWS
keeps a suspended account's volumes for a limited window and then deletes
them for good. Everything below works either way, but a real dump is worth
more than any amount of rebuilding by hand.

---

## 1. What the person doing this needs

Collect all of it before touching AWS; each missing item stops the work
halfway.

- **New AWS account** with access to EC2 in `eu-central-1`.
- **GitHub access** to `4Dream-UA/StratMaster-CS2` (a personal access token
  if the repository is private).
- **DNS panel** for `stratmaster.fun` (nic.ua), or the owner on standby to
  change two records.
- **Secrets**, from the owner — see the table in step 4. Never over plain
  chat: a password-protected archive, a password manager share, or typed
  straight into `nano .env` over the owner's shoulder.
- **A database dump** (`stratmaster_*.sql.gz`), if one exists anywhere off
  the old server. Optional — step 7 covers both cases.
- **`uploads.tar.gz`**, same deal, if one exists.

### Fill these in first

| Placeholder | Value | Where it comes from |
|---|---|---|
| `<NEW_IP>` | | the Elastic IP, after step 2 |
| `<KEY>` | | the `.pem` key pair created in step 2 |
| `<DUMP>` | | e.g. `stratmaster_20260831_210722.sql.gz`, if there is one |

---

## 2. The box

EC2 → Instances → Launch an instance:

- **Name** `stratmaster-prod`
- **AMI** Ubuntu Server 24.04 LTS (64-bit x86)
- **Type** `t3.small`. Not `t3.micro` — 1 GB swaps hard during the frontend
  image build and the whole app crawls; that was a real incident on the old
  box.
- **Key pair** → Create new, RSA, `.pem`, downloaded once. On Windows:

  ```powershell
  icacls "$env:USERPROFILE\.ssh\stratmaster-prod.pem" /inheritance:r /grant:r "$($env:USERNAME):R"
  ```

- **Security group**, new, inbound only:

  | Type | Port | Source |
  |---|---|---|
  | SSH | 22 | **My IP** — the IP of whoever is doing this |
  | HTTP | 80 | Anywhere |
  | HTTPS | 443 | Anywhere |

  Not 5432, not 6379. The production compose keeps both off the host.
- **Storage** 20 GB gp3.

Then EC2 → Elastic IPs → **Allocate**, then Actions → **Associate** → this
instance. Without it the address changes on every stop/start and the DNS
records go stale while looking perfectly correct.

Also worth doing on a fresh account: Billing → Budgets → a monthly budget
with an email alert. A frozen account is what put this document here.

```bash
ssh -i ~/.ssh/<KEY>.pem ubuntu@<NEW_IP>
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker ubuntu
exit          # log back in for the group to apply
```

---

## 3. Code

```bash
git clone https://github.com/4Dream-UA/StratMaster-CS2.git
cd StratMaster-CS2
export COMPOSE_FILE=docker-compose.prod.yml     # re-run after every reconnect
```

`backup_db.sh` and `restore_db.sh` call plain `docker compose`, which would
otherwise pick the dev file.

---

## 4. Secrets

```bash
cp .env.sample .env
nano .env
```

| Key | Where it comes from |
|---|---|
| `BOT_TOKEN` | @BotFather → the production bot. **Not** the dev bot's token |
| `CRYPTOPAY_TOKEN` | @CryptoBot → Crypto Pay → My Apps |
| `OPENAI_API_KEY` | the owner's OpenAI account — blank disables the support assistant |
| `POSTGRES_PASSWORD` | generate a new one: `openssl rand -hex 24` |
| `DATABASE_URL` | must repeat that same password |
| `SECRET_KEY` | generate: `openssl rand -hex 32` |
| `WEBAPP_URL` | `https://stratmaster.fun` |
| `DEBUG` | `False` |
| `ENVIRONMENT` | `production` |
| `NGROK_*` | leave blank — that's the dev tunnel |

`POSTGRES_PASSWORD` and `SECRET_KEY` are new on purpose: nothing outside this
box depends on them, and the old values are on a machine nobody controls any
more. The same goes the other way — if any key was ever pasted into a chat,
rotate it at the source rather than carrying it over.

---

## 5. DNS

The domain still points at the dead box, and Let's Encrypt validates over
public DNS, so this has to happen **before** the certificate.

At nic.ua, in the `stratmaster.fun` records:

| Type | Name | Value |
|---|---|---|
| A | `@` | `<NEW_IP>` |
| A | `www` | `<NEW_IP>` |

Set TTL to 300 while you work. Then wait for it:

```bash
dig +short stratmaster.fun          # must return <NEW_IP>, not the old one
```

Do not continue until it does. A certificate attempt against stale DNS fails
and counts against the limit of five per domain per week.

---

## 6. Certificate, then the stack

nginx will not start without a certificate, and certbot needs port 80 free,
so the certificate comes first and standalone:

```bash
sudo docker run --rm -p 80:80 \
  -v stratmaster-cs2_certbot_conf:/etc/letsencrypt \
  -v stratmaster-cs2_certbot_www:/var/www/certbot \
  certbot/certbot certonly --standalone \
  -d stratmaster.fun -d www.stratmaster.fun \
  --email <owner's email> --agree-tos --no-eff-email
```

Volume names are `<project>_<volume>`, the project being the checkout
directory lowercased; confirm with `docker volume ls` if the paths look
wrong.

Now bring everything up:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f backend      # wait for "Application startup complete"
```

Migrations run on backend start. On an empty database they also seed the
maps, the cases and the two forum categories, so the app is usable
immediately — just without content.

---

## 7. Data

### A — there is a dump

```bash
# from the machine holding it
scp -i ~/.ssh/<KEY>.pem <DUMP> uploads.tar.gz ubuntu@<NEW_IP>:~/
```

```bash
mkdir -p backups && mv ~/<DUMP> backups/
FORCE=1 ./scripts/restore_db.sh backups/<DUMP>
docker run --rm -v stratmaster-cs2_uploads_data:/v -v ~:/in alpine \
  tar xzf /in/uploads.tar.gz -C /v
docker compose restart backend
```

A dump from an older schema is fine — the backend migrates it on start.

### B — there is no dump

The database is empty apart from what the migrations seed. What has to be
rebuilt, in this order:

1. **An admin.** The owner opens the Mini App once so the account exists,
   then:

   ```bash
   docker compose exec -T db psql -U stratmaster -d stratmaster_db \
     -c "UPDATE users SET is_admin = true WHERE username = '<owner's telegram handle>';"
   ```

2. **Map images.** Admin → Maps → upload a cover for each seeded map.
   Uploads go to the `uploads_data` volume, so they survive redeploys.
3. **Strategies.** Admin → Strategies → New. The tactical editor is where
   the paths, grenade trajectories and timings are drawn.
4. **Paid users.** This is the part that cannot be recovered from the app:
   balances, premium and inventory lived only in the lost database.
   @CryptoBot → Crypto Pay → My Apps → the payment history lists every paid
   invoice with its amount and date. Matching those against the people who
   complain, premium can be granted by hand:

   ```bash
   docker compose exec -T db psql -U stratmaster -d stratmaster_db -c \
     "UPDATE wallets SET subscription_expires_at = now() + interval '30 days' \
      WHERE user_id = (SELECT id FROM users WHERE username = '<handle>');"
   ```

   `reconcile_invoices.py` does **not** help here — it works from invoice
   rows that this database no longer has.

Either way, expect to tell users plainly that accounts were restored from a
backup of a given date, or rebuilt. That is cheaper than a week of support
tickets asking why premium disappeared.

---

## 8. Telegram and payments

Nothing changed domain-side, but verify, because a dead server leaves
half-configured integrations behind:

- @BotFather → `/setmenubutton` → the production bot → `https://stratmaster.fun`
- @BotFather → `/setdomain` → `stratmaster.fun`
- @CryptoBot → Crypto Pay → My Apps → **Webhooks** →
  `https://stratmaster.fun/api/webhooks/cryptopay`

The webhook is the only path that credits a wallet. If it points anywhere
else, money is taken and nothing arrives.

---

## 9. Verify

```bash
curl -I https://stratmaster.fun                        # 200, valid certificate
curl -s https://stratmaster.fun/api/settings
curl -I https://stratmaster.fun/api/webhooks/cryptopay  # 401 — alive, rejects unsigned
```

Then by hand: open the Mini App from the bot, sign in, check that an image
loads, send the bot `/start`, and make one small real payment to confirm the
balance moves.

---

## 10. Backups, properly this time

The lesson of this document is that a backup living on the server it backs up
is not a backup. Set the schedule, then get the dumps off the box.

```bash
crontab -e
```

```cron
0 3 * * * cd /home/ubuntu/StratMaster-CS2 && COMPOSE_FILE=docker-compose.prod.yml ./scripts/backup_db.sh >> backup.log 2>&1
0 4 * * 1 cd /home/ubuntu/StratMaster-CS2 && docker compose -f docker-compose.prod.yml exec -T frontend nginx -s reload
```

The first is the nightly dump (14 days kept), the second reloads nginx so
renewed certificates are actually served — certbot renews in its own
container and cannot signal nginx across containers.

Then, weekly, off the server — to a laptop, S3 in a *different* account, or
anywhere that does not die with this box:

```bash
scp -i ~/.ssh/<KEY>.pem ubuntu@<NEW_IP>:~/StratMaster-CS2/backups/stratmaster_*.sql.gz .
```

```bash
docker run --rm -v stratmaster-cs2_uploads_data:/v -v $(pwd):/out alpine \
  tar czf /out/uploads.tar.gz -C /v .
```

---

## What goes wrong

**Certificate fails with a DNS error.** The A records haven't propagated.
Check with `dig +short stratmaster.fun` and wait — retrying burns the weekly
quota of five.

**nginx won't start.** No certificate in `certbot_conf`. Check:
`docker run --rm -v stratmaster-cs2_certbot_conf:/v alpine ls /v/live/stratmaster.fun`

**502 Bad Gateway.** nginx resolved the backend before it was up:
`docker compose restart frontend`.

**Images referenced but missing.** The database was restored but
`uploads.tar.gz` wasn't — the strategies are intact, their pictures aren't.

**The bot answers every other message.** Two pollers on one token. The dev
stand on someone's laptop must use the dev bot's token, never production's.

**`docker compose down -v` deletes the database.** `-v` removes named
volumes, `postgres_data` included. Use plain `down`.

**Permission denied on docker.** Log out and back in after `usermod`.
