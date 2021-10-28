# qscache

A package for caching Django querysets with type hinting in mind.

## Requirements

 - Django >= 3.0.12,<4.0.0
 - django-redis == 5.0

## Installation

    pip install qscache
    
## Versioning
This package is young so consider pining it with the exact version of package in production.
Patch releases don't include any backward incompatible changes but major and minor releases may include backward incompatible changes.

## Example
Our purpose is to keep the API simple and easy-to-use.
You must give the `BaseCacheManager` class to your cache classes kinda like how you create models in Django. For example:

in `models.py`:

	from django.db import models  
	from django.contrib.auth import get_user_model  

	
	User = get_user_model()

	  
	class Example(models.Model):  
		"""Example
		A simple example Django model like before
		"""
	      
		user = models.ForeignKey(User, on_delete=models.CASCADE,  related_name="example_user")  
	    users = models.ManyToManyField(User, related_name="examples")  
	    is_active = models.BooleanField(default=True)  


in `cache.py`:
	    
	from django.http import Http404
	from qscache import BaseCacheManager
	
	from .models import Example


	class ExampleCacheManager(BaseCacheManager[Example]):
	
		# These are all the options you have but only model is required.
		model = Example
		cache_key = "example" 
		related_objects = ["user"]
		prefetch_related_objects = ["users"] 
		use_prefetch_related_for_list = True 
		list_timeout = 86400  # 1 day
		detail_timeout = 60  # 1 minute
		exception_class = Http404

	example_cache_manager = ExampleCacheManager()
	
This is all you need to do. now you are good to use your cache manager.

    # This is the equivalent to Example.objects.all()
    # It hits database first time we fetch example list
    # But later we fetch data from cache until cache is expired
    # It returns Queryset[Example]
    example_list = example_cache_manager.all()

	# This is the equivalent to Example.objects.get(pk=1)
	# It hits database first time we fetch example list
    # But later we fetch data from cache until cache is expired
    # It returns an Example instance
	example_object = example_cache_manager.get(
		unique_identifier=1,  # pk = 1
		filter_kwargs={"pk": 1},
	)
Now let's see a better example in `rest_framework`:

    from rest_framework.viewsets import ModelViewSet

	from qscache import clear_cache_detail, clear_cache_keys
	
	from .models import Example
	from .cache import example_cache_manager
	from .serializers import ExampleSerializer


	class ExampleViewSet(ModelViewSet):
	
		serializer_class = ExampleSerializer
		http_method_names = ["get", "post", "put"]

		def get_queryset(self):  
		    example_list = example_cache_manager.all()  
		    return example_list

		def get_object(self):  
		    pk = self.kwargs.get(self.lookup_field)  
		    obj = province_cache_manager.get(
			    unique_identifier=pk, 	
			    filter_kwargs={"pk": pk},
		    )  
		    self.check_object_permissions(self.request, obj)  
		    return obj
		
		@clear_cache_keys(keys=[example_cache_manager.get_cache_key()])
		def perform_create(self, serializer):
			serializer.save()

		@clear_cache_keys(
			manager=example_cache_manager, 
			additional_fields=[example_cache_manager.get_cache_key()],
		)
		def perform_update(self, serializer): 
			return serializer.save()
	
Here the queries for our `list` and `retrieve` actions will be cached.
Now after we create an object we delete our list cache so next time we get our list cache will be updated. And after updating an object we delete our list cache key and the object from cache, so next time when we get our list and object they will be updated and cached again.
Now you have a cached `ModelViewSet`.
It was easy, wasn't it?

## Developer Guide

Now lets look at how everything is working by detail.


`BaseCacheManager` options:

 - **model:** This is the only required field that you should specify in your model cache manager. We use this model to query database and fetch data.
 - **cache_key:** The default value is `None`. If it's `None` we use the model lowercase class name. if you want to override it just use a string as cache key. We use this cache key as  our cache key separator from other model cache keys. So make sure it's unique. Defaults to `None`.
	 1. `cache_key` is our list cache key. `cache_manager.all()` will be stored in `cache_key`.
	 2. `{cache_key}_{unique_identifier}` is our detail cache key. if your unique identifier is pk(for example 1) then your detail cache key is `{cache_key}_1`. `cache_manager.get()` uses this cache key. your unique identifier can be anything but make sure it's unique so your objects won't be overridden in cache. For example `slug`, `username`, etc.
 - **related_objects:** If your model has foreign keys and you want to use `select_related` in your queries. Just pass a list containing your foreign key field names. Defaults to `None`.
 - **prefetch_related_objects:** if you wanna use `prefetch_related` in your query just add a list containing your many to many fields. Defaults to `None`.
 - **use_prefetch_related_for_list:** Your list query can be heavy and you may not need to `prefetch_related` for your list query but you need it for the detail of your objects. If it's True then we use `prefetch_related_objects` for our list query but if not we don't use `prefetch_related_objects` for our list even though it's set we only use it for getting an object not getting list of objects. Defaults to `True`.
 - **list_timeout:** This is the timeout of your list cache key in seconds. Defaults to 86400 (1 day).
 - **detail_timeout:**  This is the timeout of your detail cache key in seconds. Defaults to 60 (1 minute).
 - **exception_class:** This the exception that we raise when object is not found in `cache_manager.get()` method. Defaults to `Http404`. But if you are using `rest_framework` you may want to raise `rest_framework.exceptions.NotFound` instead of `Http404`.

Here are `BaseCacheManager` that you may want to override.
Now lets look at your model `cache_manager` methods.

 - **all(suffix: Optional[str] = None, filter_kwargs: Optional[Dict[str, Any]] = None) -> QuerySet[ModelType]:** This is the equivalent to `Model.objects.all()`. But we store it in `cache_key` and we fetch it from cache if queryset was in the cache otherwise sets queryset to the cache.
	 1. **suffix: Optional[str] = None** : This suffix is added to the end of `cache_key` if provided. It's useful when you want to store a filtered queryset in cache and you also don't want to override your `cache_manager.all()` queryset.
	 2. **filter_kwargs: Optional[Dict[str, Any]] = None** : If you want to filter your queryset you can use it and pass your filter as a dict. For example `{"name__icontains": "mojix", "is_active": True}` same as Django API. but it's better to use `suffix` and `filter_kwargs` at the same time. Then you can cache your filters when you are using them so much. For example if you have a page that you show all of the active products and you want to cache your active products instead of all of the products. You can do this `product_cache_manager.all(suffix="active", filter_kwargs={"is_active": True})`.  

**Notice:** What if you wanted to filter your queryset without caching it? imagine if it was a simple search that you don't want to cache it. Remember that `cache_manager.all()` returns `Queryset[ModelType]`. So you can use everything on it that you do in Django and you can use it even as your model manager. look that this example below:

    cache_manager.all() # only hits db first time
    cache_manager.all(suffix="active", filter_kwargs={"is_active": True}) # only hits db first time too
	
	# This not even cached you can use all the functionallity that you had in Django
	# It executes another query because you are filtering a Django queryset
	# You can use .filter(), .annotate(), etc
	# It's like Model.objects.all().filter(is_active=True)
	# So it's not stored in cache and feel free to use it
	cache_manager.all().filter(is_active=True)
	

So far so good and easy.
More coming soon :)
