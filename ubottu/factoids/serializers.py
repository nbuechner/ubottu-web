from rest_framework import serializers
from .models import Fact

class FactSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    class Meta:
        model = Fact
        fields = ['id', 'name', 'value', 'ftype', 'author_name', 'create_date', 'change_date', 'popularity']

    def get_author_name(self, obj):
        # Assuming the author field can be null
        return obj.author.username if obj.author else None