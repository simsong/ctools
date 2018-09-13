#
# clogging.py:
# 
# Census logging methods


import logging
import logging.handlers
import os
import os.path

added_syslog = False
called_basicConfig = False
DEVLOG = "/dev/log"
DEVLOG_MAC = "/var/run/syslog"
SYSLOG_FORMAT="%(asctime)s %(filename)s:%(lineno)d (%(funcName)s) %(message)s"
LOG_FORMAT="%(asctime)s %(filename)s:%(lineno)d (%(funcName)s) %(message)s"

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
        if os.path.exists(DEVLOG):
            handler = logging.handlers.SysLogHandler(address=DEVLOG, facility=facility)
        elif os.path.exists(DEVLOG_MAC):
            handler = logging.handlers.SysLogHandler(address=DEVLOG_MAC, facility=facility)
        else:
            return              # no dev log
        formatter = logging.Formatter(SYSLOG_FORMAT)
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        added_syslog = True
    

def setup(level='INFO',
          syslog=False,
          filename=None,
          facility=logging.handlers.SysLogHandler.LOG_LOCAL1,
          format=LOG_FORMAT):
    """Set up logging as specified by ArgumentParse. Checks to see if it was previously called and, if so, does a fast return."""
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


if __name__=="__main__":
    setup_syslog()
    assert added_syslog==True
    logging.error("By default, error gets logged but info doesn't")
