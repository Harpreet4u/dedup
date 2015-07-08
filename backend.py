# For all Db, cache and search connections

import redis

# Redis file datastore.
redis_file = None

def init():
    global redis_file
    
    redis_file = redis.Redis(port=6379)
