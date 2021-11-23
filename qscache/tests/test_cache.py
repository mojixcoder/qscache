from django.test import TestCase
from django.db.models.query import QuerySet
from django.core.cache import cache
from django.http import Http404
from django.conf import settings
from django.db import connection, reset_queries  # noqa
from django.contrib.auth import get_user_model

from django_redis import get_redis_connection

from qscache import clear_cache_keys, clear_cache_detail

from example_app.models import Example
from example_app.cache import (
    example_cache_manager,
    example_cache_user_prefetch_related_manager,
)

# Create your tests here.


class ExampleTestCase(TestCase):  # noqa
    """
    Test Cache Manager
    """

    @staticmethod
    def setUpClass():  # noqa
        settings.DEBUG = True
        super(ExampleTestCase, ExampleTestCase).setUpClass()

    def setUp(self) -> None:
        get_redis_connection("default").flushall()

    def tearDown(self) -> None:
        get_redis_connection("default").flushall()

    def test_all(self) -> None:
        """
        Test if objects list are stored in cache
        """
        example_object = Example(title="MojixCoder", text="Mojix Coder", number=1010)
        example_object.save()

        example_list = example_cache_manager.all()
        first_object = example_list.first()

        cache_keys = cache.keys("*")

        self.assertEqual(
            cache.ttl(example_cache_manager.get_cache_key()),
            example_cache_manager.list_timeout,
        )
        self.assertEqual(first_object.pk, example_object.pk)
        self.assertEqual(example_list.count(), 1)
        self.assertIn(example_cache_manager.get_cache_key(), cache_keys)
        self.assertIsInstance(example_list, QuerySet)

    def test_get(self) -> None:
        """
        Test if the object is stored in cache
        """
        example_object = Example(title="MojixCoder", text="Mojix Coder", number=1010)
        example_object.save()

        obj = example_cache_manager.get(
            unique_identifier=example_object.pk,
            filter_kwargs={"pk": example_object.pk},
        )
        detail_cache_key = example_cache_manager.get_detail_cache_key(
            unique_identifier=example_object.pk
        )

        cache_keys = cache.keys(f"{example_cache_manager.get_cache_key()}_*")

        self.assertEqual(
            cache.ttl(detail_cache_key), example_cache_manager.detail_timeout
        )
        self.assertEqual(obj, example_object)
        self.assertIn(detail_cache_key, cache_keys)
        self.assertIsInstance(obj, Example)

    def test_all_with_filter_and_suffix(self) -> None:
        example_object1 = Example.objects.create(
            title="MojixCoder1", text="Mojix Coder1", number=10101
        )
        example_object2 = Example.objects.create(
            title="MojixCoder2", text="Mojix Coder2", number=10102
        )

        filter_kwargs = {"title": "MojixCoder1", "number__lte": 10101}
        example_list = example_cache_manager.all(
            suffix="first_one", filter_kwargs=filter_kwargs
        )

        cache_key = example_cache_manager._get_cache_key_with_suffix(suffix="first_one")

        queryset_in_cache = cache.get(cache_key)

        self.assertEqual(cache.ttl(cache_key), example_cache_manager.list_timeout)
        self.assertEqual(example_list.count(), 1)
        self.assertNotEqual(queryset_in_cache, None)
        self.assertIn(example_object1, example_list)
        self.assertNotIn(example_object2, example_list)

    def test_get_with_filter(self) -> None:
        example_object = Example.objects.create(
            title="MojixCoder1", text="Mojix Coder1", number=10101
        )

        filter_kwargs = {"title": "404"}
        obj = example_cache_manager.get(
            unique_identifier=example_object.pk,
            filter_kwargs=filter_kwargs,
            raise_exception=False,  # if raise_exception is False then we don't raise Http404 instead we return None
        )

        cache_key = example_cache_manager.get_detail_cache_key(
            unique_identifier=example_object.pk
        )

        # This should be None if object is not found
        obj_in_cache = cache.get(cache_key)

        self.assertEqual(
            cache.ttl(cache_key), 0
        )  # ttl is 0 when cache key is not found. (django-redis)
        self.assertEqual(obj_in_cache, None)
        self.assertEqual(obj, None)
        self.assertNotIn(cache_key, cache.keys(f"{example_cache_manager.cache_key}_*"))

    def test_get_raise_exception(self) -> None:
        example_object = Example.objects.create(
            title="MojixCoder1", text="Mojix Coder1", number=10101
        )

        with self.assertRaises(Http404):
            filter_kwargs = {"title": "404"}
            obj = example_cache_manager.get(  # raise_exception is True by default
                unique_identifier=example_object.pk,
                filter_kwargs=filter_kwargs,
            )

        cache_key = example_cache_manager.get_detail_cache_key(
            unique_identifier=example_object.pk
        )

        self.assertEqual(cache.get(cache_key), None)
        self.assertNotIn(cache_key, cache.keys(f"{example_cache_manager.cache_key}_*"))

    def test_all_select_related(self) -> None:
        user = get_user_model().objects.create_user(
            username="mojixcoder",
            password="1234",
            email="mojixcoder@gmail.com",
            first_name="Mojix",
            last_name="Coder",
        )
        example_object = Example.objects.create(
            user=user, title="MojixCoder1", text="Mojix Coder1", number=10101
        )

        example_list = example_cache_manager.all()

        obj = example_list.first()

        reset_queries()

        # Because we have used select_related on user field so this field shouldn't execute another query
        first_name = obj.user.first_name

        self.assertEqual(first_name, user.first_name)
        self.assertEqual(len(connection.queries), 0)  # 0 new queries executed

    def test_all_prefetch_related(self) -> None:
        user1 = get_user_model().objects.create_user(
            username="mojixcoder1",
            password="12341",
            email="mojixcoder1@gmail.com",
            first_name="Mojix1",
            last_name="Coder1",
        )
        user2 = get_user_model().objects.create_user(
            username="mojixcoder2",
            password="12342",
            email="mojixcoder2@gmail.com",
            first_name="Mojix2",
            last_name="Coder2",
        )
        user3 = get_user_model().objects.create_user(
            username="mojixcoder3",
            password="12343",
            email="mojixcoder3@gmail.com",
            first_name="Mojix3",
            last_name="Coder3",
        )
        example_object = Example.objects.create(
            title="MojixCoder1", text="Mojix Coder1", number=10101
        )

        example_object.users.add(user1)
        example_object.users.add(user2)
        example_object.users.add(user3)

        example_list = example_cache_manager.all()
        obj = example_list.first()

        reset_queries()

        for user in obj.users.all():
            first_name = user.first_name

        self.assertEqual(len(connection.queries), 0)  # 0 new queries executed

    def test_all_select_related_and_prefetch_related(self) -> None:
        user1 = get_user_model().objects.create_user(
            username="mojixcoder1",
            password="12341",
            email="mojixcoder1@gmail.com",
            first_name="Mojix1",
            last_name="Coder1",
        )
        user2 = get_user_model().objects.create_user(
            username="mojixcoder2",
            password="12342",
            email="mojixcoder2@gmail.com",
            first_name="Mojix2",
            last_name="Coder2",
        )
        user3 = get_user_model().objects.create_user(
            username="mojixcoder3",
            password="12343",
            email="mojixcoder3@gmail.com",
            first_name="Mojix3",
            last_name="Coder3",
        )
        example_object = Example.objects.create(
            user=user3, title="MojixCoder1", text="Mojix Coder1", number=10101
        )

        example_object.users.add(user1)
        example_object.users.add(user2)

        example_list = example_cache_manager.all()
        obj = example_list.first()

        reset_queries()

        first_name = obj.user.first_name

        for user in obj.users.all():
            first_name = user.first_name

        self.assertEqual(len(connection.queries), 0)  # 0 new queries executed

    def test_get_select_related(self) -> None:
        user = get_user_model().objects.create_user(
            username="mojixcoder1",
            password="12341",
            email="mojixcoder1@gmail.com",
            first_name="Mojix1",
            last_name="Coder1",
        )
        example_object = Example(
            user=user, title="MojixCoder", text="Mojix Coder", number=1010
        )
        example_object.save()

        obj = example_cache_manager.get(
            unique_identifier=example_object.pk,
            filter_kwargs={"pk": example_object.pk},
        )

        reset_queries()

        first_name = obj.user.first_name

        self.assertEqual(len(connection.queries), 0)  # 0 new queries executed
        self.assertEqual(first_name, user.first_name)

    def test_get_prefetch_related(self) -> None:
        user1 = get_user_model().objects.create_user(
            username="mojixcoder1",
            password="12341",
            email="mojixcoder1@gmail.com",
            first_name="Mojix1",
            last_name="Coder1",
        )
        user2 = get_user_model().objects.create_user(
            username="mojixcoder2",
            password="12342",
            email="mojixcoder2@gmail.com",
            first_name="Mojix2",
            last_name="Coder2",
        )
        user3 = get_user_model().objects.create_user(
            username="mojixcoder3",
            password="12343",
            email="mojixcoder3@gmail.com",
            first_name="Mojix3",
            last_name="Coder3",
        )
        example_object = Example.objects.create(
            title="MojixCoder1", text="Mojix Coder1", number=10101
        )

        example_object.users.add(user1)
        example_object.users.add(user2)
        example_object.users.add(user3)

        obj = example_cache_manager.get(
            unique_identifier=example_object.pk,
            filter_kwargs={"pk": example_object.pk},
        )

        reset_queries()

        for user in obj.users.all():
            first_name = user.first_name

        self.assertEqual(len(connection.queries), 0)  # 0 new queries executed

    def test_get_select_related_and_prefetch_related(self) -> None:
        user1 = get_user_model().objects.create_user(
            username="mojixcoder1",
            password="12341",
            email="mojixcoder1@gmail.com",
            first_name="Mojix1",
            last_name="Coder1",
        )
        user2 = get_user_model().objects.create_user(
            username="mojixcoder2",
            password="12342",
            email="mojixcoder2@gmail.com",
            first_name="Mojix2",
            last_name="Coder2",
        )
        user3 = get_user_model().objects.create_user(
            username="mojixcoder3",
            password="12343",
            email="mojixcoder3@gmail.com",
            first_name="Mojix3",
            last_name="Coder3",
        )
        example_object = Example.objects.create(
            user=user3, title="MojixCoder1", text="Mojix Coder1", number=10101
        )

        example_object.users.add(user1)
        example_object.users.add(user2)

        obj = example_cache_manager.get(
            unique_identifier=example_object.pk,
            filter_kwargs={"pk": example_object.pk},
        )

        reset_queries()

        first_name = obj.user.first_name

        for user in obj.users.all():
            first_name = user.first_name

        self.assertEqual(len(connection.queries), 0)  # 0 new queries executed

    def test_dont_use_prefetch_related_for_list(self) -> None:
        user1 = get_user_model().objects.create_user(
            username="mojixcoder1",
            password="12341",
            email="mojixcoder1@gmail.com",
            first_name="Mojix1",
            last_name="Coder1",
        )
        example_object = Example.objects.create(
            user=user1, title="MojixCoder1", text="Mojix Coder1", number=10101
        )

        example_object.users.add(user1)

        examples = example_cache_user_prefetch_related_manager.all()

        example_obj_from_cache = examples[0]

        reset_queries()

        for user in example_obj_from_cache.users.all():
            first_name = user.first_name

        # 1 new query is executed because we don't prefetch_related objects in list query when use_prefetch_related_for_list is False
        self.assertEqual(len(connection.queries), 1)

        obj = example_cache_user_prefetch_related_manager.get(
            unique_identifier=example_object.pk,
            filter_kwargs={"pk": example_object.pk},
        )

        reset_queries()

        for user in obj.users.all():
            first_name = user.first_name

        self.assertEqual(len(connection.queries), 0)

    def test_clear_cache_keys_decorator(self) -> None:
        example_list = example_cache_manager.all()

        self.assertIn(example_cache_manager.cache_key, cache.keys("*"))

        @clear_cache_keys(keys=[example_cache_manager.cache_key])
        def create_example_object() -> None:
            example_object = Example(
                title="MojixCoder", text="Mojix Coder", number=1010
            )
            example_object.save()

        create_example_object()

        # Cache key is removed from cache
        # So next time when we call .all() cache will be updated
        self.assertNotIn(example_cache_manager.cache_key, cache.keys("*"))

    def test_clear_cache_detail(self) -> None:
        example_object = Example(title="MojixCoder", text="Mojix Coder", number=1010)
        example_object.save()

        example_obj = example_cache_manager.get(
            unique_identifier=example_object.pk, filter_kwargs={"pk": example_object.pk}
        )

        cache_key = example_cache_manager.get_detail_cache_key(example_object.pk)

        self.assertIn(cache_key, cache.keys("*"))

        @clear_cache_detail(manager=example_cache_manager)
        def update_example_object() -> Example:
            example_object.title = "I am updated"
            example_object.save()
            return example_object
        
        update_example_object()

        self.assertNotIn(cache_key, cache.keys("*"))
