import logging

from collections.abc import Iterator
from httpx import ConnectError as HTTPXConnectError
from httpcore import ConnectError as HTTPCoreConnectError
from telegram import Update
from telegram.error import NetworkError
from telegram.ext import Application, CommandHandler, ContextTypes

from .cogs import downloader_commands, error_handler, general_commands
from .utils import env

logger = logging.getLogger(__name__)


async def bad_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Raise an error to trigger the error handler."""
    await context.bot.wrong_method_name()  # type: ignore[attr-defined]


def _create_application(use_local_api: bool) -> Application:
    """Create and configure a telegram Application instance."""
    builder = Application.builder().token(env.BOT_TOKEN).concurrent_updates(True)

    if use_local_api:
        builder = (
            builder.local_mode(True)
            .base_url(f"{env.LOCAL_BOT_API_URL}/bot")
            .base_file_url(f"{env.LOCAL_BOT_API_URL}/file/bot")
        )

    application = builder.build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("bad_command", bad_command))
    application.add_handlers(general_commands)
    application.add_handlers(downloader_commands)

    # error handler
    application.add_error_handler(error_handler)

    return application


def _iter_causes(error: BaseException | None) -> Iterator[BaseException]:
    current = error
    while current is not None:
        yield current
        current = current.__cause__


def _is_connect_error(error: BaseException | None) -> bool:
    connect_errors = (HTTPXConnectError, HTTPCoreConnectError, ConnectionError, OSError)
    return any(isinstance(err, connect_errors) for err in _iter_causes(error))


def _run_application(use_local_api: bool) -> None:
    """Run the application and optionally retry without the local API server."""
    # Propagate the runtime mode so other modules (e.g., downloader) know the
    # actual backend being used. This is important when we fall back from the
    # local Bot API server to Telegram's hosted API.
    env.TELEGRAM_LOCAL = use_local_api

    application = _create_application(use_local_api)

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except NetworkError as exc:
        if use_local_api and _is_connect_error(exc):
            logger.warning(
                "Local Bot API at %s is unreachable (%s). Falling back to Telegram's hosted Bot API.",
                env.LOCAL_BOT_API_URL,
                exc,
            )
            _run_application(False)
        else:
            raise


def main() -> None:
    """Entrypoint that starts the bot."""
    _run_application(env.TELEGRAM_LOCAL)
