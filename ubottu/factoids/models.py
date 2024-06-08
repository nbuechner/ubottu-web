from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# Define Author model
class Author(models.Model):
    name = models.CharField(max_length=64)

def get_sentinel_author():
    # This assumes 'Author' model is already defined as shown above
    return Author.objects.get_or_create(name='deleted')[0]
class Fact(models.Model):
    name = models.CharField(max_length=32)
    value = models.TextField()
    FTYPE_CHOICES = (
        ("REPLY", "Reply"),
        ("ALIAS", "Alias")
    )
    ftype = models.CharField(
        max_length=32,
        choices=FTYPE_CHOICES,
        default="REPLY"
    )
    
    id = models.BigAutoField(primary_key=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    room = models.CharField(null=True, default=None, max_length=128)
    create_date = models.DateTimeField("date published", default=timezone.now)
    change_date = models.DateTimeField("date changed", default=timezone.now)
    popularity = models.IntegerField(default=0)
    def __str__(self):
        return self.name

    def was_published_recently(self):
        return self.create_date >= timezone.now() - datetime.timedelta(days=7)
