"""Temporary worker bootstrap; Celery replaces this loop in task 2."""

from time import sleep


if __name__ == "__main__":
    while True:
        sleep(60)
