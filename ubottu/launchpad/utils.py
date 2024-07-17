import redis
import json
import traceback
from . launchpad_singleton import get_launchpad

# Connect to Redis
cache = redis.Redis(host='localhost', port=6379, db=0)


def fetch_group_members(group_name, recurse=False):
    try:
        #Try to fetch from cache first
        cached_result = cache.get(f"group_members_{group_name}")
        if cached_result:
            return json.loads(cached_result)

        launchpad = get_launchpad()
        group = launchpad.people[group_name]
        
        group_members = set()
        for person in group.members:
            print(person)
            if not person.is_team:
                group_members.add(person.name)
                continue

        # MXIDs should be generated for individuals only
        print(group_members)
        mxids = ['@' + member + ':ubuntu.com' for member in group_members]
        result = {'group_members': tuple(group_members), 'group_name': group_name, 'mxids': mxids}

        # Cache the result with expiration time of 30 minutes (1800 seconds)
        cache.setex(f"group_members_{group_name}", 1800, json.dumps(result))

        return result
    except KeyError as e:
        print(f"Group with name {group_name} was not found. Error: {e}")
        print(traceback.format_exc())
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        print(traceback.format_exc())
        return False
