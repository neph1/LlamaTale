""" This file stores various caches for LLM related things. """





event_cache = {}
look_cache = {}
tell_cache = {}

def generate_hash(item: str) -> int:
    """ Generates a hash for an item. """
    return hash(item)

def cache_event(event: str, event_hash: int = -1) -> int:
    """ Adds an event to the cache. 
    Generates a hash if none supplied"""
    if hash == -1:
        event_hash = generate_hash(event)
    if event_cache.get(event_hash) == None:
        event_cache[event_hash] = event
    return event_hash

def get_events(event_hashes: [int]) -> str:
    """ Gets events from the cache. """
    return ", ".join([event_cache.get(event_hash, '') for event_hash in event_hashes])

def cache_look(look: str, look_hash: int = -1) -> int:
    """ Adds an event to the cache. 
    Generates a hash if none supplied"""
    if hash == -1:
        look_hash = generate_hash(look)
    if look_cache.get(look_hash) == None:
        look_cache[look_hash] = look
    return look_hash

def get_looks(look_hashes: [int]) -> str:
    """ Gets an event from the cache. """
    return ", ".join([look_cache.get(look_hash, '') for look_hash in look_hashes])


def cache_tell(tell: str, tell_hash: int = -1) -> int:
    """ Adds a tell to the cache. 
    Generates a hash if none supplied"""
    if hash == -1:
        tell_hash = generate_hash(tell)
    if tell_cache.get(tell_hash) == None:
        tell_cache[tell_hash] = tell
    return tell_hash

def get_tells(tell_hashes: [int]) -> str:
    """ Gets tells from the cache. """
    return ", ".join([tell_cache.get(tell_hash, '') for tell_hash in tell_hashes])

