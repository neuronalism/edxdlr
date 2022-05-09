# credit: https://stackoverflow.com/a/34964369
# license: CC BY-SA 3.0

import multiprocessing
import logging
import signal
from logging.handlers import QueueHandler, QueueListener

def setup_logger():   
    logging_level = logging.INFO
    q = multiprocessing.Queue()
    # this is the handler for all log records
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    # ql gets records from the queue and sends them to the handler
    ql = QueueListener(q, handler)
    ql.start()

    logger = logging.getLogger()
    logger.setLevel(logging_level)
    # add the handler to the logger so records from this process are handled
    logger.addHandler(handler)

    return ql, q

def signal_handler(sig, frame):
    global pool
    pool.terminate()
    pool.join()
    raise(KeyboardInterrupt)

def pool_init(q):
    # all records from worker processes go to qh and then into q
    logging_level = logging.INFO
    qh = QueueHandler(q)
    logger = logging.getLogger()
    logger.setLevel(logging_level)
    logger.addHandler(qh)
    # make it responsive to Ctrl-C
    signal.signal(signal.SIGINT, signal_handler)
