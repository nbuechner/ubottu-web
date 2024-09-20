import redis
import json
import traceback
from .launchpad_singleton import get_launchpad

# Connect to Redis
cache = redis.Redis(host='localhost', port=6379, db=0)

def fetch_matrix_accounts(profile_id):
    try:
        # Try to fetch from cache first
        cached_result = cache.get(f"matrix_{profile_id}")
        if cached_result:
            return json.loads(cached_result)

        # Fetch Launchpad API data
        launchpad = get_launchpad()
        person = launchpad.people[profile_id]

        # Fetch social accounts by platform (Matrix)
        matrix_accounts = person.getSocialAccountsByPlatform(platform='Matrix platform')

        # Extract the Matrix IDs
        matrix_ids = []
        for account in matrix_accounts:
            username = account['identity']['username']
            homeserver = account['identity']['homeserver']
            matrix_id = f"@{username}:{homeserver}"
            matrix_ids.append(matrix_id)

        # Cache the result with expiration time of 30 minutes (1800 seconds)
        cache.setex(f"matrix_{profile_id}", 1800, json.dumps(matrix_ids))

        return matrix_ids
        
    except KeyError as e:
        print(f"Profile with name {profile_id} was not found. Error: {e}")
        print(traceback.format_exc())
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        print(traceback.format_exc())
        return False


def fetch_group_members(group_name, recurse=False):
    try:
        # Try to fetch from cache first
        cached_result = cache.get(f"group_members_{group_name}")
        if cached_result:
            return json.loads(cached_result)

        # Fetch the group from the Launchpad API
        launchpad = get_launchpad()
        group = launchpad.people[group_name]
        
        group_members = set()
        for person in group.members:
            if not person.is_team:
                group_members.add(person.name)
            # Optional recursion to get sub-teams' members
            elif recurse:
                sub_group_members = fetch_group_members(person.name, recurse=True)
                group_members.update(sub_group_members['group_members'])

        # Generate MXIDs for individual members
        mxids = [f"@{member}:ubuntu.com" for member in group_members]
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
