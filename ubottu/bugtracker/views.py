from django.http import HttpResponse, Http404
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from datetime import datetime
from rest_framework import status
#from launchpadlib.launchpad import Launchpad
from .launchpad_singleton import get_launchpad
import pytz
import json
import requests

@api_view(['GET'])
@cache_page(60 * 15)  # Cache for 15 minutes
def get_launchpad_bug(request, bug_id):
    #Bug 2059145 in filament (Ubuntu) "please remove filament from noble" [Undecided, In Progress] https://launchpad.net/bugs/2059145
    package = ''
    release_name = ''
    target_link = ''
    target_name = ''
    series = ''
    series_display_name = ''
    cachedir = "~/.launchpadlib/cache/"
    try:
        launchpad = get_launchpad()
        bug = launchpad.bugs[int(bug_id)]
        for task in bug.bug_tasks:
            if task.target.name:
                package=task.target.name
            if task.target_link:
                target_link = task.target_link
        
        return Response({'id': bug.id, 'title': bug.title, 'target_link': target_link, 'status': task.status, \
                         'importance': task.importance, 'self_link': bug.self_link, 'link': bug.web_link, 'target_link': target_link, 'package': package})

    except KeyError as e:
        # Handle the case where the bug is not found
        print(f"Bug with ID {bug_id} was not found. Error: {e}")
        return Response({'error': 'Bug not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # Handle other potential exceptions
        print(f"An error occurred: {e}")
        print(f"Error processing request for launchpad bug {bug_id}: {str(e)}")
        return Response({'error': 'An error occurred processing your request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
@cache_page(60 * 15)  # Cache for 15 minutes
def get_github_bug(request, owner, repo, bug_id):
    #Issue 81 in NVIDIA/nvidia-container-toolkit "Can't install due to no public key being available for Ubuntu" [Open]
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{bug_id}"
        response = requests.get(url)
        if response.status_code == 404:
            # If the GitHub API returns a 404 status code, return an appropriate response
            return Response({'error': 'GitHub bug not found'}, status=status.HTTP_404_NOT_FOUND)
        bug = response.json()
        issue_id = bug['number']  # GitHub API uses 'number' as the issue ID in the repository
        owner_repo = bug['repository_url'].split('/')[-2:]  # Extracts owner and repo from the URL
        description = bug['title']
        state = bug['state']
        return Response({'id':issue_id, 'description': description, 'state': state, 'project': '/'.join(owner_repo)})
    except KeyError as e:
        # Handle the case where the bug is not found
        print(f"Bug with ID {bug_id} was not found. Error: {e}")
        return Response({'error': 'Bug not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # Handle other potential exceptions
        print(f"An error occurred: {e}")
        print(f"Error processing request for launchpad bug {bug_id}: {str(e)}")
        return Response({'error': 'An error occurred processing your request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    