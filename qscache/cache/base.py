import warnings
from typing import Any, List, Dict, Optional, TypeVar, Type, Generic

from django.core.cache import cache
from django.db.models import QuerySet, Model
from django.http import Http404


ModelType = TypeVar("ModelType", bound=Model)


class BaseCacheManager(Generic[ModelType]):
    """Base Cache Manager"""

    model: Type[ModelType]
    cache_key: Optional[str] = None
    related_objects: Optional[List[str]] = None
    prefetch_related_objects: Optional[List[str]] = None
    use_prefetch_related_for_list: bool = True
    list_timeout: int = 86400  # 1 day
    detail_timeout: int = 60  # 1 minute
    exception_class: Type[Exception] = Http404

    def _get_cache_key(self, cache_key: Optional[str] = None) -> str:
        if cache_key is not None:
            return cache_key
        return self.model.__name__.lower()

    def get_cache_key(self) -> str:
        return self._get_cache_key(self.cache_key)

    def get_detail_cache_key(self, unique_identifier) -> str:
        detail_cache_key = f"{self.get_cache_key()}_{unique_identifier}"
        return detail_cache_key

    def _get_all_queryset(self) -> QuerySet[ModelType]:
        if self.related_objects is None and self.prefetch_related_objects is None:
            queryset = self.model.objects.all()
        elif self.related_objects is not None and self.prefetch_related_objects is None:
            queryset = self.model.objects.select_related(*self.related_objects).all()
        elif (
            self.related_objects is None
            and self.prefetch_related_objects is not None
            and self.use_prefetch_related_for_list
        ):
            queryset = self.model.objects.all().prefetch_related(
                *self.prefetch_related_objects
            )
        elif (
            self.related_objects is None
            and self.prefetch_related_objects is not None
            and not self.use_prefetch_related_for_list
        ):
            queryset = self.model.objects.all()
        elif (
            self.related_objects is not None
            and self.prefetch_related_objects is not None
            and self.use_prefetch_related_for_list
        ):
            queryset = (
                self.model.objects.select_related(*self.related_objects)  # noqa
                .all()
                .prefetch_related(*self.prefetch_related_objects)
            )
        else:
            queryset = self.model.objects.select_related(
                *self.related_objects  # noqa
            ).all()
        return queryset

    def get_all_queryset(
        self,
        queryset: Optional[QuerySet[ModelType]],
        key: str,
        filter_kwargs: Optional[Dict[str, Any]] = None,
    ) -> QuerySet[ModelType]:
        if queryset is not None:
            return queryset
        queryset = self._get_all_queryset()
        if filter_kwargs is not None:
            queryset = queryset.filter(**filter_kwargs)
        cache.set(key=key, value=queryset, timeout=self.list_timeout)
        return queryset

    def _get_cache_key_with_suffix(self, suffix: str):
        cache_key = f"{self.get_cache_key()}_{suffix}"
        return cache_key

    def all(
        self,
        suffix: Optional[str] = None,
        filter_kwargs: Optional[Dict[str, Any]] = None,
    ) -> QuerySet[ModelType]:
        """all
        Gets querysets from cache if queryset was in the cache otherwise sets queryset to the cache.

        Parameters:
            suffix: Optional[str]
                - Added to the end of the `cache_key` if provided.
            filter_kwargs: Optional[Dict[str, Any]]
                - Filters queryset if provided.

        Returns:
            queryset: QuerySet[ModelType]
                - Cached queryset.
        """
        if filter_kwargs is not None and suffix is None:
            warnings.warn(
                "You are caching a filtered queryset without adding suffix. This may affect your raw cached queryset."
            )

        cache_key = (
            self.get_cache_key()
            if suffix is None
            else self._get_cache_key_with_suffix(suffix)
        )

        queryset = self.get_all_queryset(
            queryset=cache.get(cache_key),
            key=cache_key,
            filter_kwargs=filter_kwargs,
        )

        return queryset

    def _get_detail_queryset(self, filter_kwargs: Dict[str, Any]) -> ModelType:
        if self.related_objects is None and self.prefetch_related_objects is None:
            obj = self.model.objects.get(**filter_kwargs)
        elif self.related_objects and self.prefetch_related_objects is None:
            obj = self.model.objects.select_related(*self.related_objects).get(  # noqa
                **filter_kwargs
            )
        elif self.related_objects is None and self.prefetch_related_objects:
            obj = self.model.objects.prefetch_related(
                *self.prefetch_related_objects
            ).get(**filter_kwargs)
        else:
            obj = (
                self.model.objects.select_related(*self.related_objects)
                .prefetch_related(*self.prefetch_related_objects)
                .get(**filter_kwargs)
            )
        return obj

    def get(
        self,
        unique_identifier: Any,
        filter_kwargs: Dict[str, Any],
        raise_exception: bool = True,
    ) -> Optional[ModelType]:
        """get
        Gets an object from cache if object was in the cache otherwise sets object to the cache.

        Parameters:
            unique_identifier: Any
                - Try to get the object from cache with unique_identifier
            filter_kwargs: Optional[Dict[str, Any]]
                - When we try to get object with unique_identifier but object was not found then we use filter_kwargs
                to get object
            raise_exception: bool = True
                - If it's true then we raise Http404 when object was not found

        Returns:
            obj: Optional[ModelType]
                - Cached object or None if raise_exception=False and object was not found.
        """
        try:
            cache_key = self.get_detail_cache_key(unique_identifier)
            obj = cache.get(cache_key)
            if obj is not None:
                return obj
            else:
                obj = self._get_detail_queryset(filter_kwargs)
                cache.set(
                    key=cache_key,
                    value=obj,
                    timeout=self.detail_timeout,
                )
                return obj
        except:  # noqa
            if raise_exception:
                raise self.exception_class
            else:
                return None

    def clear_cache(self) -> None:
        """
        Clear caches that start with `cache_key`
        """
        self.clear_cache_list()
        self.clear_cache_detail()

    def clear_cache_list(self) -> None:
        """
        Clear cache with `cache_key` key
        """
        cache.delete(self.get_cache_key())

    def clear_cache_detail(self) -> None:
        """
        Clear caches that start with `cache_key_*`, means all the cache except the list cache key.
        """
        cache.delete_many(cache.keys(f"{self.get_cache_key()}_*"))
