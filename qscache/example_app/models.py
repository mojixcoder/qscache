from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.


class Example(models.Model):
    """Example
    An example model for testing

    Note:
        All of this fields are just for testing and don't mean anything
    """

    user = models.ForeignKey(
        get_user_model(),
        null=True,
        on_delete=models.CASCADE,
        related_name="example_user",
    )
    users = models.ManyToManyField(get_user_model(), related_name="examples")
    title = models.CharField(max_length=255)
    text = models.TextField()
    number = models.IntegerField()

    def __str__(self):
        return self.title
