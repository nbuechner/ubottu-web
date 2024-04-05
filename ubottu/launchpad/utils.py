import redis
import json
from bugtracker.launchpad_singleton import get_launchpad

# Connect to Redis
cache = redis.Redis(host='localhost', port=6379, db=0)

def fetch_group_members(group_name):
    try:
        # Try to fetch from cache first
        cached_result = cache.get(f"group_members_{group_name}")
        if cached_result:
            return json.loads(cached_result)

        # If not cached, fetch from Launchpad
        launchpad = get_launchpad()
        group = launchpad.people[group_name]
        group_members = [person.name for person in group.members]
        mxids = ['@' + person.name + ':ubuntu.com' for person in group.members]
        result = {'group_members': group_members, 'group_name': group_name, 'mxids': mxids}

        # Cache the result with expiration time of 30 minutes (1800 seconds)
        cache.setex(f"group_members_{group_name}", 1800, json.dumps(result))

        return result
    except KeyError as e:
        print(f"Group with name {group_name} was not found. Error: {e}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        print(f"Error processing request for launchpad group {group_name}: {str(e)}")
        return False
