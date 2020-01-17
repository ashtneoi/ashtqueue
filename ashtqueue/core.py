#!/usr/bin/env python3

import time
from uuid import uuid4

import redis


class Client:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.ident = str(uuid4())

    def try_lock_slow(self, name, timeout_sec=30):
        if self.redis_client.exists(f"lock:{name}"):
            # Why no context manager? :(
            pubsub = None
            try:
                pubsub = self.redis_client.pubsub()
                start = time.monotonic()
                end = start + timeout_sec
                while True:
                    now = time.monotonic()
                    if now >= end:
                        return False
                    pubsub.subscribe(f"next:{name}")
                    # Why doesn't timeout work? :(
                    msg = pubsub.get_message(True, timeout=(end - now))
                    print(msg)
                    if msg is not None \
                            and msg['data'] == self.ident.encode('ascii'):
                        return self.try_lock_fast()
                    time.sleep(0.5)
            finally:
                if pubsub is not None:
                    pubsub.reset()
        else:
            return self.try_lock_fast()


if __name__ == '__main__':
    c = Client(redis.Redis())
    print(c.ident)
    c.try_lock_slow('hi', timeout_sec=300)
