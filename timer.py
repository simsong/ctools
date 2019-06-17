import time


class Timer:    
    def __init__(self,message=None):
        if '%' in message:
            self.message = message
        else:
            self.message = message + " %f"

    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start
        if self.message:
            print(self.message % self.interval)
