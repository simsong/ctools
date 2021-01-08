import sys
import time

def print_stderr(s):
    print(s,file=sys.stderr)

class Timer:
    def __init__(self,message='Elapsed time:',notifier=print_stderr):
        self.notifier = notifier
        if '%' in message:
            self.message = message
        else:
            self.message = message + " %f seconds"

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.interval = self.end - self.start
        if (self.message is not None) and (self.notifier is not None):
            self.notifier(self.message % self.interval)
