"""
APScheduler tasks: morning digest, deadline reminders, weekly report.
"""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models import User, Task, TaskStatus, WorkspaceMember, Workspace, Reminder
from app.bots.manager import bot_manager

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


async def send_morning_digest():
    """Send morning digest to all users who have it enabled."""
    logger.info("Running morning digest job")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.notify_morning_digest == True).where(User.is_active == True)
        )
        users = result.scalars().all()

        for user in users:
            try:
                # Get user's tasks due today or overdue
                today_end = datetime.utcnow().replace(hour=23, minute=59, second=59)
                tasks_result = await session.execute(
                    select(Task)
                    .where(Task.assignee_id == user.id)
                    .where(Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS]))
                    .where(Task.due_date <= today_end)
                    .order_by(Task.due_date)
                )
                tasks = tasks_result.scalars().all()

                if not tasks:
                    continue

                lines = [f"☀️ <b>Доброе утро, {user.first_name}!</b>\n\nЗадачи на сегодня:\n"]
                for task in tasks[:10]:
                    icon = "🔴" if task.due_date < datetime.utcnow() else "📋"
                    due = task.due_date.strftime("%H:%M") if task.due_date else ""
                    lines.append(f"{icon} {task.title} {due}")

                text = "\n".join(lines)

                # Find a workspace token for this user
                mem_result = await session.execute(
                    select(WorkspaceMember)
                    .join(Workspace)
                    .where(WorkspaceMember.user_id == user.id)
                    .where(Workspace.is_active == True)
                )
                memberships = mem_result.scalars().all()

                for membership in memberships:
                    ws = await session.get(Workspace, membership.workspace_id)
                    if ws and ws.telegram_bot_token in bot_manager.get_tokens():
                        bot, _ = bot_manager._bots[ws.telegram_bot_token]
                        await bot.send_message(chat_id=user.telegram_id, text=text)
                        break

            except Exception as e:
                logger.error(f"Digest error for user {user.id}: {e}")


async def send_deadline_reminders():
    """Check and send deadline reminders."""
    logger.info("Running deadline reminder job")
    async with AsyncSessionLocal() as session:
        now = datetime.utcnow()
        soon = now + timedelta(hours=24)

        result = await session.execute(
            select(Reminder)
            .where(Reminder.is_sent == False)
            .where(Reminder.remind_at <= soon)
            .where(Reminder.remind_at >= now)
        )
        reminders = result.scalars().all()

        for reminder in reminders:
            try:
                task = await session.get(Task, reminder.task_id)
                user = await session.get(User, reminder.user_id)
                if not task or not user:
                    continue

                due_str = task.due_date.strftime("%d.%m %H:%M") if task.due_date else "—"
                text = (
                    f"⏰ <b>Напоминание!</b>\n\n"
                    f"📋 {task.title}\n"
                    f"📅 Дедлайн: {due_str}"
                )

                # Find bot for user
                mem_result = await session.execute(
                    select(WorkspaceMember)
                    .join(Workspace)
                    .where(WorkspaceMember.user_id == user.id)
                    .where(Workspace.is_active == True)
                )
                for membership in mem_result.scalars().all():
                    ws = await session.get(Workspace, membership.workspace_id)
                    if ws and ws.telegram_bot_token in bot_manager.get_tokens():
                        bot, _ = bot_manager._bots[ws.telegram_bot_token]
                        await bot.send_message(chat_id=user.telegram_id, text=text)
                        reminder.is_sent = True
                        break

            except Exception as e:
                logger.error(f"Reminder error: {e}")

        await session.commit()


def setup_scheduler():
    scheduler.add_job(
        send_morning_digest,
        CronTrigger(hour=6, minute=0),  # 06:00 UTC = 09:00 MSK
        id="morning_digest",
        replace_existing=True,
    )
    scheduler.add_job(
        send_deadline_reminders,
        CronTrigger(minute="*/30"),  # every 30 min
        id="deadline_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started")
