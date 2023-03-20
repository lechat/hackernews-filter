import redis


class RedisPool:
    __instance = None

    def __new__(cls, host='localhost', port=6379):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.host = host
            cls.__instance.port = port
            cls.__instance.redis_pool = redis.ConnectionPool(
                host=host, port=port, db=0
            )

        return cls.__instance

    def __enter__(self):
        self.connection = redis.Redis(connection_pool=self.redis_pool)
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def safe_read(self, key):
        conn = redis.Redis(connection_pool=self.redis_pool)
        with conn.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    value = pipe.get(key)
                    pipe.reset()
                    pipe.execute()
                except redis.exceptions.WatchError:
                    continue

                break

            return value
