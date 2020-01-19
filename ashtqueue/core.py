#!/usr/bin/env python3

import time
import traceback
from datetime import datetime
from uuid import uuid4

import redis


DB_VERSION = '1'

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S UTC'


class DbVersionMismatch(Exception):
    pass


class Client:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.ident = str(uuid4())

    def add_to_queue(self, name):
        if self.redis_client.get('db-version') != DB_VERSION:
            raise DbVersionMismatch
        self.redis_client.rpush(f'queue:{name}', self.ident)

    def try_lock_slow(self, name, msg, timeout_sec=30):
        if self.redis_client.get('db-version') != DB_VERSION:
            raise DbVersionMismatch

        if self.try_lock_fast(name, msg):
            return True

        # Why no context manager? :(
        pubsub = None
        try:
            pubsub = \
                self.redis_client.pubsub(ignore_subscribe_messages=True)
            start = time.monotonic()
            end = start + timeout_sec
            while True:
                now = time.monotonic()
                if now >= end:
                    return False
                pubsub.subscribe(f'next:{name}')
                # Why doesn't timeout work? :(
                msg = pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=(end - now)
                )
                print(f"msg: {msg}")
                if msg is not None \
                        and msg['data'] == self.ident:
                    return self.try_lock_fast(name, msg)
                time.sleep(0.5)
            return False
        finally:
            if pubsub is not None:
                pubsub.reset()

    def try_lock_fast(self, name, msg):
        with self.redis_client.pipeline() as pipe:
            pipe.watch(f'lock:{name}', f'queue:{name}', 'db-version')

            if pipe.exists(f'lock:{name}'):
                return False
            if pipe.lindex(f'queue:{name}', 0) != self.ident:
                return False
            if pipe.get('db-version') != DB_VERSION:
                raise DbVersionMismatch

            pipe.multi()
            pipe.lpop(f'queue:{name}')
            pipe.rpush(
                f'lock:{name}', datetime.utcnow().strftime(DATETIME_FORMAT)
            )
            pipe.rpush(
                f'lock:{name}', msg
            )
            try:
                pipe.execute(raise_on_error=True)  # lazy
                return True
            except redis.ResponseError:
                traceback.print_exc()

        if self.redis_client.get('db-version') != DB_VERSION:
            raise DbVersionMismatch
        return False


if __name__ == '__main__':
    c = Client(redis.Redis(decode_responses=True))
    print(c.ident)
    c.add_to_queue('hi')
    while not c.try_lock_slow('hi', 'just chilling', timeout_sec=5):
        print("trying again")
