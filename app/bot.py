import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import get_settings
from app.db import SessionLocal
from app.enums import ProcessingPreset
from app.logging import configure_logging
from app.services.job_manager import JobManager

logger = logging.getLogger(__name__)

PRESET_CALLBACK_PREFIX = "preset:"
PENDING_LINKS: dict[int, str] = {}


def _help_text() -> str:
    return (
        "Отправьте публичную ссылку Яндекс Диска на ZIP-архив или используйте:\n"
        "/process <ссылка> [preset]\n"
        "/status <job_id>\n"
        "/cancel <job_id>\n"
        "/last\n"
        "/presets\n"
        "/logo"
    )


async def _with_manager(callback):
    async with SessionLocal() as session:
        manager = JobManager(session)
        return await callback(manager)


async def cmd_start(message: Message) -> None:
    await message.answer("Сервис принимает ZIP-архивы с Яндекс Диска.\n" + _help_text())


async def cmd_help(message: Message) -> None:
    await message.answer(_help_text())


async def cmd_presets(message: Message) -> None:
    await message.answer(
        "Доступные режимы:\n"
        "Локальная проработка:\n"
        "natural — деликатная локальная коррекция\n"
        "balanced — локальная коррекция по умолчанию\n"
        "strong — более заметная локальная коррекция\n"
        "Общая проработка:\n"
        "global_natural — деликатная общая коррекция кадра\n"
        "global_balanced — общая коррекция по умолчанию\n"
        "global_strong — более заметная общая коррекция кадра\n"
        "default — алиас balanced"
    )


async def cmd_logo(message: Message) -> None:
    await message.answer("Используются два PNG-логотипа с прозрачностью в нижних углах изображения.")


async def cmd_process(message: Message, command: CommandObject) -> None:
    if command.args is None:
        await message.answer("Нужна ссылка: /process <ссылка> [preset]")
        return
    parts = command.args.strip().split(maxsplit=1)
    source_url = parts[0]
    if len(parts) == 2:
        try:
            preset = ProcessingPreset(parts[1].strip().lower())
        except ValueError:
            await message.answer("Неизвестный preset. Используйте /presets")
            return
        await _process_url(message, source_url, preset)
        return
    await _ask_for_preset(message, source_url)


async def cmd_status(message: Message, command: CommandObject) -> None:
    if command.args is None:
        await message.answer("Нужен идентификатор задачи: /status <job_id>")
        return

    async def action(manager: JobManager):
        return await manager.get_job(command.args.strip())

    job = await _with_manager(action)
    if job is None:
        await message.answer("Задача не найдена")
        return
    await message.answer(_format_job(job))


async def cmd_cancel(message: Message, command: CommandObject) -> None:
    if command.args is None:
        await message.answer("Нужен идентификатор задачи: /cancel <job_id>")
        return

    async def action(manager: JobManager):
        return await manager.cancel_job(command.args.strip())

    job = await _with_manager(action)
    if job is None:
        await message.answer("Задача не найдена")
        return
    await message.answer(f"Статус задачи {job.id}: {job.status}")


async def cmd_last(message: Message) -> None:
    async def action(manager: JobManager):
        return await manager.get_last_job(message.from_user.id)

    job = await _with_manager(action)
    if job is None:
        await message.answer("У вас пока нет задач")
        return
    await message.answer(_format_job(job))


async def on_url_message(message: Message) -> None:
    text = (message.text or "").strip()
    await _ask_for_preset(message, text)


async def on_preset_selected(callback: CallbackQuery) -> None:
    if callback.data is None or not callback.data.startswith(PRESET_CALLBACK_PREFIX):
        await callback.answer()
        return

    source_url = PENDING_LINKS.get(callback.from_user.id)
    if not source_url:
        await callback.answer("Ссылка уже устарела, отправьте ее заново", show_alert=True)
        return

    preset_value = callback.data.removeprefix(PRESET_CALLBACK_PREFIX)
    try:
        preset = ProcessingPreset(preset_value)
    except ValueError:
        await callback.answer("Неизвестный preset", show_alert=True)
        return

    PENDING_LINKS.pop(callback.from_user.id, None)
    await callback.answer(f"Выбран режим: {preset}")
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await _process_url(callback.message, source_url, preset)


async def _ask_for_preset(message: Message, source_url: str) -> None:
    PENDING_LINKS[message.from_user.id] = source_url
    await message.answer(
        "Выберите пресет для обработки:",
        reply_markup=_preset_keyboard(),
    )


def _preset_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Local Natural", callback_data=f"{PRESET_CALLBACK_PREFIX}{ProcessingPreset.NATURAL}"),
                InlineKeyboardButton(text="Local Balanced", callback_data=f"{PRESET_CALLBACK_PREFIX}{ProcessingPreset.BALANCED}"),
                InlineKeyboardButton(text="Local Strong", callback_data=f"{PRESET_CALLBACK_PREFIX}{ProcessingPreset.STRONG}"),
            ],
            [
                InlineKeyboardButton(
                    text="Global Natural",
                    callback_data=f"{PRESET_CALLBACK_PREFIX}{ProcessingPreset.GLOBAL_NATURAL}",
                ),
                InlineKeyboardButton(
                    text="Global Balanced",
                    callback_data=f"{PRESET_CALLBACK_PREFIX}{ProcessingPreset.GLOBAL_BALANCED}",
                ),
                InlineKeyboardButton(
                    text="Global Strong",
                    callback_data=f"{PRESET_CALLBACK_PREFIX}{ProcessingPreset.GLOBAL_STRONG}",
                ),
            ],
        ]
    )


async def _process_url(message: Message, source_url: str, preset: ProcessingPreset) -> None:
    async def action(manager: JobManager):
        return await manager.create_job(
            telegram_user_id=message.from_user.id,
            telegram_chat_id=message.chat.id,
            source_url=source_url,
            preset=preset,
        )

    try:
        job = await _with_manager(action)
    except ValueError as error:
        await message.answer(str(error))
        return
    await message.answer(f"Задача создана: {job.id}\nСтатус: {job.status}\nРежим: {job.preset}")


def _format_job(job) -> str:
    lines = [
        f"Задача: {job.id}",
        f"Статус: {job.status}",
        f"Режим: {job.preset}",
        f"Файлов всего: {job.total_files}",
        f"Обработано: {job.processed_files}",
        f"Пропущено: {job.skipped_files}",
    ]
    if job.result_url:
        lines.append(f"Результат: {job.result_url}")
    if job.error_message:
        lines.append(f"Ошибка: {job.error_message}")
    return "\n".join(lines)


async def run_bot() -> None:
    configure_logging()
    settings = get_settings()
    bot = Bot(settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.message.register(cmd_start, Command("start"))
    dispatcher.message.register(cmd_help, Command("help"))
    dispatcher.message.register(cmd_presets, Command("presets"))
    dispatcher.message.register(cmd_logo, Command("logo"))
    dispatcher.message.register(cmd_process, Command("process"))
    dispatcher.message.register(cmd_status, Command("status"))
    dispatcher.message.register(cmd_cancel, Command("cancel"))
    dispatcher.message.register(cmd_last, Command("last"))
    dispatcher.message.register(on_url_message, F.text)
    dispatcher.callback_query.register(on_preset_selected, F.data.startswith(PRESET_CALLBACK_PREFIX))
    await dispatcher.start_polling(bot)
