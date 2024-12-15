import os
import sys
import logging
import datetime
import pytest
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Define a global format string for log alignment
LOG_FORMAT = "%(asctime)s %(levelname)-8s: %(filename)-20s:%(funcName)-20s:%(lineno)-4d >>> %(message)s"

# Define custom logging levels
SUCCESS_LOG_LEVEL = 21
APP_LOG_LEVEL = 15
PROD_LOG_LEVEL = 14
DATABASE_LOG_LEVEL = 13
CHAT_LOG_LEVEL = 12
QUERY_LOG_LEVEL = 11
TESTING_LOG_LEVEL = 9
VARIABLES_LOG_LEVEL = 2
PEDANTIC_LOG_LEVEL = 1

# Register custom log levels
CUSTOM_LEVELS = {
    SUCCESS_LOG_LEVEL: "SUCCESS",
    APP_LOG_LEVEL: "APP",
    PROD_LOG_LEVEL: "PROD",
    DATABASE_LOG_LEVEL: "DATABASE",
    CHAT_LOG_LEVEL: "CHAT",
    QUERY_LOG_LEVEL: "QUERY",
    TESTING_LOG_LEVEL: "TESTING",
    VARIABLES_LOG_LEVEL: "VARIABLES",
    PEDANTIC_LOG_LEVEL: "PEDANTIC"
}
for level, name in CUSTOM_LEVELS.items():
    logging.addLevelName(level, name)

# ANSI escape sequences for colors
class LogColors:
    """ANSI escape sequences for various log levels to colorize log output."""
    DARK_RED, BRIGHT_RED = '\033[31m', '\033[91m'
    ORANGE, GOLD, YELLOW = '\033[33m', '\033[93m', '\033[93m'
    GREEN, DARKGREEN, LIGHTGREEN = '\033[92m', '\033[32m', '\033[92m'
    LIGHTBLUE, BLUE, INDIGO, VIOLET = '\033[94m', '\033[94m', '\033[34m', '\033[35m'
    RESET, WHITE, BLACK = '\033[0m', '\033[37m', '\033[30m'

# Custom Formatter
class ColoredFormatter(logging.Formatter):
    """Custom formatter to add color and emojis to log messages for console output."""
    COLORS = {
        logging.CRITICAL: f"{LogColors.DARK_RED}🚨 ",
        logging.ERROR: f"{LogColors.BRIGHT_RED}❌ ",
        logging.WARNING: f"{LogColors.ORANGE}⚠️ ",
        logging.INFO: f"{LogColors.GREEN}ℹ️ ",
        logging.DEBUG: f"{LogColors.BLUE}🐛 ",
        SUCCESS_LOG_LEVEL: f"{LogColors.LIGHTGREEN}✅ ",
        APP_LOG_LEVEL: f"{LogColors.INDIGO}🚀 ",
        PROD_LOG_LEVEL: f"{LogColors.VIOLET}🏭 ",
        DATABASE_LOG_LEVEL: f"{LogColors.DARKGREEN}🗄️ ",
        CHAT_LOG_LEVEL: f"{LogColors.LIGHTBLUE}💬 ",
        QUERY_LOG_LEVEL: f"{LogColors.GOLD}🔍 ",
        TESTING_LOG_LEVEL: f"{LogColors.YELLOW}🧪 ",
        VARIABLES_LOG_LEVEL: f"{LogColors.WHITE}🔢 ",
        PEDANTIC_LOG_LEVEL: f"{LogColors.BLACK}🔬 ",
    }

    def format(self, record):
        log_fmt = self.COLORS.get(record.levelno, self.COLORS[logging.INFO]) + self._fmt
        formatter = logging.Formatter(log_fmt)
        message = formatter.format(record) + LogColors.RESET
        try:
            return message
        except UnicodeEncodeError:
            return message.encode('ascii', 'replace').decode('ascii')

    def formatException(self, ei):
        try:
            return super().formatException(ei)
        except UnicodeEncodeError:
            return super().formatException(ei).encode('ascii', 'replace').decode('ascii')

class FileFormatter(logging.Formatter):
    def format(self, record):
        return logging.Formatter(LOG_FORMAT).format(record)

class PytestFormatter:
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        if report.when == "call":
            if report.passed:
                logging.success(f"✅ Test passed: {item.name}")
            elif report.failed:
                logging.error(f"❌ Test failed: {item.name}")
            elif report.skipped:
                logging.warning(f"⏭️ Test skipped: {item.name}")

# Custom logger methods
def _add_custom_log_methods():
    def create_log_method(level):
        def log_method(self, message, *args, **kws):
            if self.isEnabledFor(level):
                self._log(level, message, args, **kws)
        return log_method

    custom_methods = {
        "chat": CHAT_LOG_LEVEL, "variables": VARIABLES_LOG_LEVEL,
        "pedantic": PEDANTIC_LOG_LEVEL, "prod": PROD_LOG_LEVEL,
        "query": QUERY_LOG_LEVEL, "database": DATABASE_LOG_LEVEL,
        "testing": TESTING_LOG_LEVEL, "app": APP_LOG_LEVEL, "success": SUCCESS_LOG_LEVEL
    }
    for method_name, level in custom_methods.items():
        setattr(logging.Logger, method_name, create_log_method(level))

_add_custom_log_methods()

# Set an environment directory
def set_log_path(env_var):
    env_path = os.getenv(env_var.upper())
    if env_path and not os.path.exists(env_path):
        os.makedirs(env_path)
    return env_path

# Get a logger with specified settings
def get_logger(name=None, log_level=None, log_path=None, log_file=None, delimiter='_', runtime=False, log_format=None):
    logger = logging.getLogger(name or __name__)
    log_levels = {
        'CRITICAL': logging.CRITICAL, 'ERROR': logging.ERROR, 'WARNING': logging.WARNING,
        'SUCCESS': SUCCESS_LOG_LEVEL, 'APP': APP_LOG_LEVEL, 'PROD': PROD_LOG_LEVEL,
        'DATABASE': DATABASE_LOG_LEVEL, 'INFO': logging.INFO, 'DEBUG': logging.DEBUG,
        'TESTING': TESTING_LOG_LEVEL, 'CHAT': CHAT_LOG_LEVEL, 'QUERY': QUERY_LOG_LEVEL,
        'VARIABLES': VARIABLES_LOG_LEVEL, 'PEDANTIC': PEDANTIC_LOG_LEVEL,
    }
    desired_level = log_levels.get(log_level, logging.INFO) if log_level else logger.level or logging.INFO
    logger.setLevel(desired_level)
    logger.propagate = False

    console_formatter = ColoredFormatter(LOG_FORMAT if log_format in (None, "default") else log_format)
    file_formatter = FileFormatter(LOG_FORMAT if log_format in (None, "default") else log_format)

    if not logger.handlers:
        if runtime:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.DEBUG)
            ch.setFormatter(console_formatter)
            logger.addHandler(ch)

        if log_path and log_file:
            os.makedirs(log_path, exist_ok=True)
            log_file_path = os.path.join(log_path, f"{log_file}{'_' if runtime else delimiter}{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') if not runtime else ''}.log")
            fh = logging.FileHandler(log_file_path)
            fh.setLevel(desired_level)
            fh.setFormatter(file_formatter)
            logger.addHandler(fh)
    else:
        for handler in logger.handlers:
            handler.setLevel(desired_level)
            handler.setFormatter(file_formatter if isinstance(handler, logging.FileHandler) else console_formatter)

    return logger

# Retrieve all loggers
def get_loggers():
    """Return a list of all logger instances."""
    return [logging.getLogger(name) for name in logging.Logger.manager.loggerDict]

# Initialize logger using provided settings
def initialise_logger(log_name='backend', log_level=None, log_dir=None, log_format='default', runtime=True):
    log_level = log_level or os.getenv("LOG_LEVEL", "DEBUG")
    log_dir = log_dir or os.getenv("LOG_PATH", "/logs")
    return get_logger(name=log_name, log_level=log_level, log_path=log_dir, log_file=log_name, runtime=runtime, log_format=log_format)
