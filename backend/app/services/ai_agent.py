"""AI support assistant — answers the first pass on support tickets.

It posts into the existing support-ticket threads as an ordinary forum user
(see the 0035 migration for why it needs a real users row), so everything
already built around tickets keeps working unchanged: the player gets the
usual Telegram notification, the thread shows up in the admin queue, and an
admin can reply over the top at any point.

Deliberately conservative about when it speaks:
  * support category only — never the Lounge,
  * never once staff have replied, so it can't talk over them,
  * never on a closed ticket,
  * at most `ai_agent_max_replies_per_thread` times in one thread,
  * not at all unless an API key is set and the admin switch is on.

Every failure path is silent and non-blocking. A ticket the assistant can't
answer is just a ticket waiting for a human, which is what it was before
this existed.
"""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.db.database import AsyncSessionLocal
from backend.app.db.models import (
    AppSettingsModel,
    ForumCategoryModel,
    ForumPostModel,
    ForumThreadModel,
    UserModel,
)

logger = logging.getLogger(__name__)

# Telegram ids are always positive, so 0 can never belong to a real account.
AGENT_TELEGRAM_ID = 0

MAX_HISTORY_MESSAGES = 12
MAX_REPLY_CHARS = 1500

# Everything in here is a fact about this app, checked against the code that
# implements it — the assistant is only worth having if it stops repeating
# what a generic chatbot would guess. It is told to defer rather than
# improvise because a confidently wrong answer about someone's money is
# worse than no answer at all.
SYSTEM_PROMPT = """You are the StratMaster CS2 support assistant, replying inside a private support ticket in the app's forum. StratMaster is a Counter-Strike 2 strategy library that runs as a Telegram Mini App.

What you know about the product:
- Premium unlocks the full strategy library. Plans are 1, 3, 6 or 12 months, or a one-off Lifetime.
- Premium is SET to the duration bought, counted from the moment of purchase - it does not stack on top of time already remaining. Buying a shorter plan while a longer one is running replaces it. The checkout warns about this before charging.
- MasterCoins (MC) are the in-app currency, pegged at 1 MC = $0.01. Minimum top-up is 10 coins. Top-ups are paid in crypto (USDT / BTC / TON) from the profile page.
- Every player has a Wallet ID, used to send coins, gift a subscription, or gift and sell cases and Premium vouchers to other players.
- Cases are bought with MasterCoins and opened for a random reward from a published pool. The odds are shown in the app before purchase under "View odds". Reward tables target an average return of about 80% of what is spent on cases overall - a long-run average across all players, never a promise for one case or one player.
- A Premium reward from a case arrives as a voucher in the inventory. The player chooses when to activate it, and activating sets Premium to exactly the number of days on the voucher. Vouchers can also be gifted or sold to other players.
- There are no refunds on cases or on coins already spent. Do not offer, promise or hint at a refund under any circumstances.

How to reply:
- Be brief and concrete. Two or three short sentences is usually right. No greeting-and-signoff padding.
- Answer in the same language the player wrote in.
- Only state things from the list above, or from what the player has told you in this ticket. Never invent prices, dates, balances, order numbers, policies or features.
- You cannot see the player's account, balance or purchases, and you have no access to any of their data. If answering would need that, say so plainly and tell them the team will pick the ticket up.
- If you are not confident, say the team will follow up rather than guessing. That is always an acceptable answer.
- Never claim to be human, and never promise anything on the team's behalf - no timelines, no compensation, no account changes.
- Plain text only. No markdown headings, no bullet lists, no links.
"""

# Appended in code, never asked of the model: the guarantee that every reply
# is marked as automated must not depend on the model remembering to do it.
# English only, deliberately — the reply above it follows whatever language
# the player wrote in, but the marker itself is a fixed product string.
SIGNATURE = "\n\n— Automated first reply. Someone from the team will follow up if this didn't sort it."


def is_configured() -> bool:
    return bool(settings.openai_api_key)


async def get_agent_user(db) -> UserModel | None:
    result = await db.execute(select(UserModel).where(UserModel.telegram_id == AGENT_TELEGRAM_ID))
    return result.scalar_one_or_none()


async def _is_enabled(db) -> bool:
    row = await db.get(AppSettingsModel, 1)
    # No settings row yet means nothing has been configured or switched off,
    # so match the column default rather than treating it as "disabled".
    return True if row is None else row.ai_agent_enabled


async def complete(messages: list[dict]) -> str | None:
    """One chat-completions call. Returns None on any failure — callers treat
    "no answer" and "the call broke" identically, because the outcome for the
    player is the same either way: the ticket waits for a human."""
    try:
        async with httpx.AsyncClient(timeout=settings.ai_agent_timeout_seconds) as client:
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=_request_body(messages),
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("AI support agent: completion request failed")
        return None

    text = (content or "").strip()
    return text[:MAX_REPLY_CHARS] if text else None


def _request_body(messages: list[dict]) -> dict:
    """`max_completion_tokens`, not `max_tokens`: the GPT-5.x family rejects
    the old name outright (400 unsupported_parameter), and it is the current
    spelling everywhere else too.

    Temperature is only sent when explicitly configured. The same family
    accepts nothing but the default and 400s on anything else, so a
    hard-coded value would make the assistant impossible to run on the model
    it ships pointed at."""
    body = {
        "model": settings.ai_agent_model,
        "messages": messages,
        "max_completion_tokens": settings.ai_agent_max_tokens,
    }
    if settings.ai_agent_temperature is not None:
        body["temperature"] = settings.ai_agent_temperature
    return body


def _build_messages(thread_title: str, posts: list[ForumPostModel], agent_id) -> list[dict]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Ticket subject: {thread_title}"},
    ]
    for post in posts[-MAX_HISTORY_MESSAGES:]:
        role = "assistant" if post.user_id == agent_id else "user"
        messages.append({"role": role, "content": post.body})
    return messages


async def reply_to_ticket(thread_id) -> bool:
    """Drafts and posts one reply to a support ticket. Opens its own session:
    it runs as a background task, after the request that scheduled it has
    returned and closed its own. Returns whether it actually posted."""
    if not is_configured():
        return False

    async with AsyncSessionLocal() as db:
        try:
            if not await _is_enabled(db):
                return False

            agent = await get_agent_user(db)
            if agent is None:
                logger.warning("AI support agent: no agent user row — is migration 0035 applied?")
                return False

            result = await db.execute(
                select(ForumThreadModel)
                .options(
                    selectinload(ForumThreadModel.category),
                    selectinload(ForumThreadModel.posts).selectinload(ForumPostModel.user),
                )
                .where(ForumThreadModel.id == thread_id)
            )
            thread = result.scalar_one_or_none()
            if thread is None or thread.category.key != "support" or thread.is_closed:
                return False

            posts = sorted(thread.posts, key=lambda p: p.created_at)
            visible = [p for p in posts if p.deleted_at is None]
            if not visible:
                return False

            # Staff have taken this one — stay out of it from here on. Judged
            # by "an admin other than the person who opened it has posted",
            # not by "an admin has posted": in a support ticket the only
            # people with access are the owner and the admins, so anyone but
            # the owner writing *is* staff joining. An admin opening their
            # own ticket is just someone with a question.
            if any(p.user.is_admin and p.user_id != thread.user_id for p in visible):
                return False
            # Never answer twice running: the last word is already ours, so
            # there is no new question on the table.
            if visible[-1].user_id == agent.id:
                return False
            if sum(1 for p in visible if p.user_id == agent.id) >= settings.ai_agent_max_replies_per_thread:
                return False

            messages = _build_messages(thread.title, visible, agent.id)
            thread_title = thread.title
        except Exception:
            logger.exception("AI support agent: could not prepare a reply")
            return False

        answer = await complete(messages)
        if not answer:
            return False

        try:
            db.add(ForumPostModel(thread_id=thread_id, user_id=agent.id, body=answer + SIGNATURE))
            # Same bump a human reply does, so the ticket sorts correctly in
            # the admin queue instead of looking untouched since the player
            # last wrote.
            thread.updated_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception:
            logger.exception("AI support agent: could not save its reply")
            await db.rollback()
            return False

    await _notify_ticket_owner(thread_id, thread_title)
    return True


async def _notify_ticket_owner(thread_id, thread_title: str) -> None:
    """The same Telegram ping a human reply sends. Kept after the commit and
    in its own try block so a notification failure can't roll back a reply
    that is already saved and visible in the app."""
    from backend.app.services.notifications import send_telegram_message

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ForumThreadModel)
                .options(selectinload(ForumThreadModel.user))
                .where(ForumThreadModel.id == thread_id)
            )
            thread = result.scalar_one_or_none()
            if thread is None:
                return
            link = None
            if settings.webapp_url:
                link = f"{settings.webapp_url.rstrip('/')}/forum?thread={thread_id}"
            await send_telegram_message(
                thread.user.telegram_id,
                f"💬 The StratMaster assistant replied to your ticket <b>{thread_title}</b>",
                web_app_url=link,
            )
    except Exception:
        logger.exception("AI support agent: could not notify the ticket owner")


async def should_handle(db, thread: ForumThreadModel, category: ForumCategoryModel, author: UserModel) -> bool:
    """Cheap pre-check on the request path, so an endpoint only schedules the
    background task when it has a chance of doing anything.

    Keyed on the author being the person the ticket belongs to. Anyone else
    posting in a support ticket is staff (only the owner and admins can see
    one at all), and staff replying is precisely when the assistant should
    keep quiet."""
    if not is_configured() or category.key != "support" or thread.is_closed:
        return False
    if author.id != thread.user_id:
        return False
    return await _is_enabled(db)
