# standard imports
import hashlib
import logging

# third-party imports
from redis import Redis

logg = logging.getLogger()


class InMemoryStore:
    cache: Redis = None


def cache_data(key: str, data: str):
    """
    :param key:
    :type key:
    :param data:
    :type data:
    :return:
    :rtype:
    """
    cache = InMemoryStore.cache
    cache.set(name=key, value=data)
    cache.persist(name=key)


def get_cached_data(key: str):
    """
    :param key:
    :type key:
    :return:
    :rtype:
    """
    cache = InMemoryStore.cache
    return cache.get(name=key)


def create_cached_data_key(identifier: bytes, salt: str):
    """
    :param identifier:
    :type identifier:
    :param salt:
    :type salt:
    :return:
    :rtype:
    """
    hash_object = hashlib.new("sha256")
    hash_object.update(identifier)
    hash_object.update(salt.encode(encoding="utf-8"))
    return hash_object.digest().hex()
