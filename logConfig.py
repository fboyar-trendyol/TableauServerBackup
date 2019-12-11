import os
import logging
from logging.handlers import RotatingFileHandler
from sensitiveFormatter import SensitiveFormatter

if os.path.isdir('logs') is False:
    os.makedirs('logs')

logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
 
fh = RotatingFileHandler('logs/tableauBackup.log', maxBytes=500000, backupCount=5)
fh.setLevel(logging.INFO)
fh.setFormatter(SensitiveFormatter('%(asctime)s - %(name)s - %(levelname)-10s - %(message)s') )
logger.addHandler(fh)
 
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(SensitiveFormatter('%(asctime)s - %(levelname)-10s - %(message)s'))
logger.addHandler(sh)

