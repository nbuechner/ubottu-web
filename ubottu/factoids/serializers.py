import re
import json
from rest_framework import serializers
from .models import Fact
from launchpad.utils import fetch_group_members

class FactSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField() 
    class Meta:
        model = Fact
        fields = ['id', 'name', 'value', 'ftype', 'author_name', 'create_date', 'change_date', 'popularity']

    def get_author_name(self, obj):
        # Assuming the author field can be null
        return obj.author.username if obj.author else None

    def get_value(self, obj):
        value = obj.value  # The original text with placeholders
        launchpad_group_pattern = r'\{launchpad_group\.([^}]+)\}'
        matches = re.findall(launchpad_group_pattern, value)
        if not matches:
            return value
        group_name = matches[0]
        members = fetch_group_members(group_name)
        if members is None:
            return value
        if 'mxids' in members:
            return value.replace( '{launchpad_group.' + group_name + '}', 'https://matrix.to/#/' + ' https://matrix.to/#/'.join(members['mxids']))

        return value
            
