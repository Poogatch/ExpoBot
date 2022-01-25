import time
from concurrent.futures import ThreadPoolExecutor
import schedule


def mytask(task_name):
    for i in range(10):
        print(task_name)
        time.sleep(10)


def myexector():
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in range(2):
            executor.submit(mytask, 'task-' + str(i))


if __name__ == '__main__':
    schedule.every(2).seconds.do(myexector)
    while True:
        schedule.run_pending()


