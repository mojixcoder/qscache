from cache.base import BaseCacheManager
from .models import Example


class ExampleCacheManager(BaseCacheManager[Example]):
    """Example Cache Manager"""

    model = Example
    cache_key = "example"
    related_objects = ["user"]
    prefetch_related_objects = ["users"]


class ExampleCacheManagerUsePrefetchRelatedForList(BaseCacheManager[Example]):
    """Example Cache Manager Use Prefetch Related Objects For List

    Tests that if `use_prefetch_related_for_list` is False we don't use it for list queryset
    but we use it in detail queryset
    """

    model = Example
    cache_key = "example"
    related_objects = ["user"]
    prefetch_related_objects = ["users"]
    use_prefetch_related_for_list = False


example_cache_manager = ExampleCacheManager()
example_cache_user_prefetch_related_manager = (
    ExampleCacheManagerUsePrefetchRelatedForList()
)
