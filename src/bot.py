import logging

from httpx import ConnectError as HTTPXConnectError
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


def _run_application(use_local_api: bool) -> None:
    """Run the application and optionally retry without the local API server."""
    application = _create_application(use_local_api)

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except NetworkError as exc:
        underlying_error = exc.__cause__
        cannot_connect_local = isinstance(underlying_error, HTTPXConnectError)

        if use_local_api and cannot_connect_local:
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
