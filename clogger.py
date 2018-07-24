#
# clogger.py:
# 
# Census logging methods


import logging
import logging.handlers

added_syslog = False
called_basicConfig = False

def shutdown():
    global added_syslog, called_basicConfig
    logging.shutdown()
    added_syslog = False
    called_basicConfig = False

def add_argument(parser):
    """Add the --loglevel argument to the ArgumentParser"""
    parser.add_argument("--loglevel", help="Set logging level",
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'], default='INFO')

def setup_syslog(facility=logging.handlers.SysLogHandler.LOG_LOCAL1):
    global added_syslog, called_basicConfig
    if not added_syslog:
        # Make a second handler that logs to syslog
        handler = logging.handlers.SysLogHandler(address="/dev/log", facility=facility)
        logging.getLogger().addHandler(handler)
        added_syslog = True
    

def setup(level='INFO',
          syslog=False,
          filename=None,
          facility=logging.handlers.SysLogHandler.LOG_LOCAL1,
          format="%(asctime)s %(filename)s:%(lineno)d (%(funcName)s) %(message)s"):
    """Set up logging as specified by ArgumentParser"""
    global called_basicConfig
    if not called_basicConfig:
        loglevel = logging.getLevelName(level)
        if filename:
            logging.basicConfig(filename=filename, format=format, level=loglevel)
        else:
            logging.basicConfig(format=format, level=loglevel)
        called_basedConig = True

    if syslog:
        setup_syslog(facility=facility)
