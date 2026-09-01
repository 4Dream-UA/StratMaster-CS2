"""Credit CryptoPay invoices that were paid while the webhook wasn't arriving.

The webhook is the only path that credits a wallet — the status endpoint the
frontend polls just reads our own row. So any stretch where CryptoPay
couldn't reach us (wrong callback URL, the server down, a bad deploy) leaves
real payments taken and coins never delivered.

This asks CryptoPay for the true status of every invoice we still have open
and settles the ones it reports as paid. It never decides on its own that
something was paid, and it goes through the same process_paid_invoice() the
webhook uses, which is idempotent — so running it twice credits nothing
twice.

Dry run by default; pass --apply to actually credit.

    docker compose -f docker-compose.prod.yml exec -T backend \
      python -m backend.app.scripts.reconcile_invoices
    docker compose -f docker-compose.prod.yml exec -T backend \
      python -m backend.app.scripts.reconcile_invoices --apply
"""
import asyncio
import sys

import httpx
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.db.database import AsyncSessionLocal
from backend.app.db.models import CryptoInvoiceModel, UserModel
from backend.app.services.crypto import CRYPTOPAY_BASE_URL
from backend.app.services.payment_events import process_paid_invoice

BATCH = 100


async def cryptopay_statuses(invoice_ids: list[int]) -> dict[int, str]:
    """{invoice_id: status} straight from CryptoPay. Batched — the API caps
    how many ids one call may name."""
    statuses: dict[int, str] = {}
    async with httpx.AsyncClient(timeout=20.0) as client:
        for i in range(0, len(invoice_ids), BATCH):
            chunk = invoice_ids[i:i + BATCH]
            response = await client.get(
                f"{CRYPTOPAY_BASE_URL}/getInvoices",
                headers={"Crypto-Pay-API-Token": settings.cryptopay_token},
                params={"invoice_ids": ",".join(str(x) for x in chunk), "count": BATCH},
            )
            data = response.json()
            if not data.get("ok"):
                raise SystemExit(f"CryptoPay ответил ошибкой: {data.get('error')}")
            result = data["result"]
            # The API has returned both a bare list and {"items": [...]}
            # across versions; accept either.
            items = result.get("items", []) if isinstance(result, dict) else result
            for item in items:
                statuses[int(item["invoice_id"])] = item["status"]
    return statuses


async def main(apply: bool) -> None:
    async with AsyncSessionLocal() as db:
        pending = (await db.execute(
            select(CryptoInvoiceModel)
            .where(CryptoInvoiceModel.status != "paid")
            .order_by(CryptoInvoiceModel.created_at)
        )).scalars().all()

        if not pending:
            print("Незакрытых счетов нет — всё уже зачислено.")
            return

        print(f"Незакрытых счетов в базе: {len(pending)}. Спрашиваю статус у CryptoPay…\n")
        statuses = await cryptopay_statuses([inv.invoice_id for inv in pending])

        to_credit = []
        for inv in pending:
            real = statuses.get(inv.invoice_id, "не найден у CryptoPay")
            mark = "ОПЛАЧЕН" if real == "paid" else real
            print(f"  #{inv.invoice_id:<12} {inv.coins:>6} MC   у нас: {inv.status:<8} у CryptoPay: {mark}")
            if real == "paid":
                to_credit.append(inv)

        if not to_credit:
            print("\nОплаченных среди них нет — начислять нечего.")
            return

        total = sum(inv.coins for inv in to_credit)
        print(f"\nК зачислению: {len(to_credit)} шт., {total} MC.")

        if not apply:
            print("Это пробный прогон. Чтобы зачислить, запусти ту же команду с --apply.")
            return

        for inv in to_credit:
            settled = await process_paid_invoice(db, inv.invoice_id)
            user = (await db.execute(
                select(UserModel).where(UserModel.id == inv.user_id)
            )).scalar_one_or_none()
            who = (user.username and "@" + user.username) or (user and str(user.telegram_id)) or "?"
            print(f"  #{inv.invoice_id} → {inv.coins} MC зачислено ({who})"
                  if settled else f"  #{inv.invoice_id} → пропущен")

        print(f"\nГотово: {len(to_credit)} счетов, {total} MC.")


if __name__ == "__main__":
    asyncio.run(main(apply="--apply" in sys.argv))
