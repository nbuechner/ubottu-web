from django.http import HttpResponse, Http404
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from datetime import datetime
from rest_framework import status
from .launchpad_singleton import get_launchpad
from .utils import fetch_group_members  # Adjust the import path as necessary
import pytz
import json
import requests

@api_view(['GET'])
#@cache_page(60 * 30)  # Cache for 30 minutes
def group_members(self, group_name):
    try:
        result = fetch_group_members(group_name)
        return Response(result)
    except KeyError as e:
        # Handle the case where the bug is not found
        print(f"Group with name {group_name} was not found. Error: {e}")
        return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # Handle other potential exceptions
        print(f"An error occurred: {e}")
        print(f"Error processing request for launchpad group {group_name}: {str(e)}")
        return Response({'error': 'An error occurred processing your request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
