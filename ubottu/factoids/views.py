from django.http import HttpResponse, Http404
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Fact
from .serializers import FactSerializer
from django.shortcuts import render
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from datetime import datetime
from rest_framework import status
import pytz
import json

def index(request):
    return HttpResponse("Hello, world. You're at the factoids index.")

@api_view(['GET'])
def city_time(request, city_name):
    try:
        geolocator = Nominatim(user_agent="Ubottu", timeout=10)
        location = geolocator.geocode(city_name, exactly_one=True, language='en')
        if location is None:
            # If the location wasn't found, return an appropriate response
            return Response({'error': 'Location not found'}, status=status.HTTP_404_NOT_FOUND)

        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=location.latitude, lng=location.longitude)  # Get the timezone name
        
        if timezone_str is None:
            # If the timezone wasn't found, return an appropriate response
            return Response({'error': 'Timezone not found for the given location'}, status=status.HTTP_404_NOT_FOUND)
        
        timezone = pytz.timezone(timezone_str)
        datetime_obj = datetime.now(timezone)
        local_time = datetime_obj.strftime('%A, %d %B %Y, %H:%M')
        city_name = str(location).split(',')[0]
        data = {'location': str(location), 'city': city_name, 'local_time': local_time}
        return Response(data)
    except Exception as e:
        # Log the exception if needed
        print(f"Error processing request for city {city_name}: {str(e)}")
        # Return a JSON response indicating an error occurred
        # Returning False directly is not recommended for API responses
        return Response({'error': 'An error occurred processing your request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def list_facts(request):
    #facts = Fact.objects.all()
    sort_by = request.GET.get('sort', 'name')  # Default sort by 'name'
    allowed_sorts = ['name', 'ftype', 'popularity']
    if sort_by not in allowed_sorts:
        sort_by = 'name'  # Fallback to a safe default
    if sort_by == 'popularity':
        facts = Fact.objects.order_by('-popularity', 'name')
    else:
        facts = Fact.objects.order_by(sort_by)
    return render(request, 'factoids/list_facts.html', {'facts': facts})

class FactList(APIView):
    """
    List all Fact items or retrieve a single Fact item by name or id.
    """
    def get(self, request, *args, **kwargs):
        # Check if an 'id' parameter is provided in the URL.
        fact_id = kwargs.get('id')
        # Check if a 'name' parameter is provided in the URL.
        name = kwargs.get('name')

        if fact_id:
            # Fetching the Fact item by id.
            try:
                fact = Fact.objects.get(id=fact_id)
            except Fact.DoesNotExist:
                raise Http404("Fact not found")
        elif name:
            # Fetching the Fact item by name.
            try:
                fact = Fact.objects.get(name=name)
                fact.popularity += 1  # Increment popularity
                fact.save(update_fields=['popularity'])  # Save the change
            except Fact.DoesNotExist:
                raise Http404("Fact not found")
        else:
            # If neither 'id' nor 'name' is provided, you might want to list all facts
            # or handle the situation differently (e.g., return an error response).
            facts = Fact.objects.all()
            serializer = FactSerializer(facts, many=True)
            return Response(serializer.data)

        # Serializing the retrieved Fact item.
        serializer = FactSerializer(fact)
        return Response(serializer.data)