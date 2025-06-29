import logging
import colorlog

# LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
#
# logging.basicConfig(
#     level=logging.DEBUG,
#     format=LOG_FORMAT,
#     datefmt="%Y-%m-%d %H:%M:%S",
# )
# logger = logging.getLogger("app:bulk-transfer")
def get_logger(name="app"):
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        fmt='[%(asctime)s] [%(levelname)s] [%(name)s] %(log_color)s%(message)s',
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    ))

    logger = colorlog.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.propagate = False
    return logger