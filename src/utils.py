import progressbar
import time


def sleep_with_progess(sleep_secs):
    for i in progressbar.progressbar(range(100)):
        time.sleep(sleep_secs / 100)
