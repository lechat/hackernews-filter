from redis_pool import RedisPool
from apscheduler.schedulers.background import BackgroundScheduler

# define the function to be executed in the separate process
def page_collector():
    # put some result into Redis queue
    redis_conn.rpush('results', 'some result')


# define the function to read from the Redis queue and store the result in Redis key
def store_pages():
    # read from Redis queue
    with RedisPool() as red:
        result = red_conn.lpop('results')
        if result:
            # store the result in Redis key
            redis_conn.set('result_key', result)


def start_jobs():
    # initialize the scheduler
    scheduler = BackgroundScheduler()

    scheduler.add_job(store_pages, "interval", seconds=10)

    scheduler.start()
