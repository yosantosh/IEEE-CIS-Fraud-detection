from pathlib import Path
import logging,os, sys

from logging.handlers import RotatingFileHandler
from datetime import datetime
import sys            #---> sys.stdout : standard output yani terminal so the logger will send the logs in terminal
                    #this is extremely import mainly if we are running docker containing our app


# constanst for logging
LOG_DIR = "logs"
LOG_FILE = f"{datetime.now().strftime('%d_%m_%Y_|_%H_%M')}.log"
MAX_LOG_SIZE = 5*1024*1024        # 5mb       total in kbs
BACKUP_COUNT = 5                  # how many nos of log file you want to keep in total, if the total files are
                                # >5 then it will delete last log file


#construct log file path
current_file_path = Path(__file__)
root_dir = current_file_path.parent.parent.parent.resolve()     # its like three times cd .. cd .. cd.. so that i will be find out root dir
log_dir_path = root_dir / LOG_DIR                               #create log path

# print(log_dir_path)


def logged():
    "Logging module with RotatingFileHandler and consolehandler"

    #creating logger object 
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # logger formattor
    # Format: Time | Level | File:Line | Message
    formatter = logging.Formatter(
    "[%(asctime)s] | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"
    )

    # Create directories if they don't exist
    os.makedirs(log_dir_path, exist_ok=True)
    
    # Full log file path
    log_file_path = log_dir_path / LOG_FILE

    # Rotating file handler to delete old logs and save the disk space
    file_handler = RotatingFileHandler(log_file_path, maxBytes=MAX_LOG_SIZE,backupCount=BACKUP_COUNT,encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    #adding handlers into logger object
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


# call logged func here : so that when you imort this it will autorun without explicitely run it there using looged.setup_logging()
logged()                
