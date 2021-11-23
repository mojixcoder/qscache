from typing import TypeVar, Type, List, Optional

from django.core.cache import cache

from .base import BaseCacheManager


ManagerType = TypeVar("ManagerType", bound=BaseCacheManager)


def clear_cache_keys(keys: List[str]):
    """
    Removes the given cache keys from cache
    """

    def clear(func):
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            cache.delete_many(keys)

        return wrapper

    return clear


def clear_cache_detail(
    manager: Type[ManagerType],
    field: str = "pk",
    additional_fields: Optional[List[str]] = None,
):
    """
    Removes the detail cache key and other given cache keys from cache

    Note:
        The function must return a model instance
    """

    def clear(func):
        def wrapper(*args, **kwargs):
            obj = func(*args, **kwargs)
            detail_key = manager.get_detail_cache_key(getattr(obj, field))  # noqa
            if additional_fields is not None:
                deleted_keys = [detail_key]
                deleted_keys.append(additional_fields)
                cache.delete_many(deleted_keys)
            else:
                cache.delete(detail_key)

        return wrapper

    return clear
