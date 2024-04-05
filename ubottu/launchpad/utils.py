import redis
import json
from bugtracker.launchpad_singleton import get_launchpad

# Connect to Redis
cache = redis.Redis(host='localhost', port=6379, db=0)

def fetch_individual_or_team_members(person_or_team, launchpad):
    members = []
    if person_or_team.is_team:
        # Recursively fetch members for a team
        group = launchpad.people[person_or_team.name]
        for person in group.members:
            if person.is_team:
                ext = fetch_individual_or_team_members(person, launchpad)
                if ext and not person.is_team:
                    members.append({
                        'name': person_or_team.name,
                    })
            else:
                members.append({
                    'name': person.name,
                })
    else:
        # Append individual member details
        members.append({
            'name': person_or_team.name,
        })
    return members

def fetch_group_members(group_name):
    try:
        #Try to fetch from cache first
        cached_result = cache.get(f"group_members_{group_name}")
        if cached_result:
            return json.loads(cached_result)

        launchpad = get_launchpad()
        group = launchpad.people[group_name]
        
        group_members = []
        for person in group.members:
            ext = fetch_individual_or_team_members(person, launchpad)
            if ext:
                group_members.extend(ext)
        
        # MXIDs should be generated for individuals only
        mxids = ['@' + member['name'] + ':ubuntu.com' for member in group_members]
        result = {'group_members': group_members, 'group_name': group_name, 'mxids': mxids}

        # Cache the result with expiration time of 30 minutes (1800 seconds)
        cache.setex(f"group_members_{group_name}", 1800, json.dumps(result))

        return result
    except KeyError as e:
        print(f"Group with name {group_name} was not found. Error: {e}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
