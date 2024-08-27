
import logging
from pythonjsonlogger import jsonlogger

def setup_logger():
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s',
                                         rename_fields={'levelname': 'level', 'asctime': 'timestamp'})
    logHandler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(logHandler)
    logger.setLevel(logging.DEBUG)
