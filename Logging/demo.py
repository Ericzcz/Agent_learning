import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger("my_app")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler("app.log")
file_handler.setLevel(logging.DEBUG)

formatter = jsonlogger.JsonFormatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)

console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger.info(
    "user login",
    extra={
        "user_id": 123,
        "ip": "127.0.0.1"
    }
)
logger.debug("debug only in file")
logger.info("info in console and file")
logger.error("error in console and file")

try:
    1 / 0
except Exception:
    logger.exception("calculation failed")