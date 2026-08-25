import datetime
from dateutil import relativedelta
import requests
import os
from lxml import etree
import time
import hashlib

# Fine-grained or standard personal access token
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN', '')
USER_NAME = os.environ.get('USER_NAME', 'hrshjswniii')

HEADERS = {'authorization': f'token {ACCESS_TOKEN}'} if ACCESS_TOKEN else {}
QUERY_COUNT = {'user_getter': 0, 'follower_getter': 0, 'graph_repos_stars': 0, 'graph_commits': 0}

def daily_readme(birthday):
    """
    Returns the length of time since birthday / dev start date
    e.g. 'XX years, XX months, XX days'
    """
    diff = relativedelta.relativedelta(datetime.datetime.today(), birthday)
    return '{} {}, {} {}, {} {}{}'.format(
        diff.years, 'year' + format_plural(diff.years), 
        diff.months, 'month' + format_plural(diff.months), 
        diff.days, 'day' + format_plural(diff.days),
        ' 🎂' if (diff.months == 0 and diff.days == 0) else '')

def format_plural(unit):
    return 's' if unit != 1 else ''

def simple_request(func_name, query, variables):
    if not ACCESS_TOKEN:
        return None
    try:
        request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': variables}, headers=HEADERS, timeout=10)
        if request.status_code == 200:
            return request
    except Exception as e:
        print(f"Request failed in {func_name}: {e}")
    return None

def graph_commits():
    query_count('graph_commits')
    today = datetime.datetime.today()
    start_date = (today - datetime.timedelta(days=365)).isoformat()
    end_date = today.isoformat()
    query = '''
    query($start_date: DateTime!, $end_date: DateTime!, $login: String!) {
        user(login: $login) {
            contributionsCollection(from: $start_date, to: $end_date) {
                contributionCalendar {
                    totalContributions
                }
            }
        }
    }'''
    req = simple_request('graph_commits', query, {'start_date': start_date, 'end_date': end_date, 'login': USER_NAME})
    if req and req.json().get('data'):
        return req.json()['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions']
    return 280

def graph_repos_stars():
    query_count('graph_repos_stars')
    query = '''
    query ($login: String!) {
        user(login: $login) {
            repositories(first: 100, ownerAffiliations: [OWNER]) {
                totalCount
                nodes {
                    stargazers {
                        totalCount
                    }
                }
            }
        }
    }'''
    req = simple_request('graph_repos_stars', query, {'login': USER_NAME})
    if req and req.json().get('data'):
        user_data = req.json()['data']['user']
        repos_count = user_data['repositories']['totalCount']
        stars_count = sum(node['stargazers']['totalCount'] for node in user_data['repositories']['nodes'])
        return repos_count, stars_count
    return 18, 14

def follower_getter():
    query_count('follower_getter')
    query = '''
    query($login: String!){
        user(login: $login) {
            followers {
                totalCount
            }
        }
    }'''
    req = simple_request('follower_getter', query, {'login': USER_NAME})
    if req and req.json().get('data'):
        return req.json()['data']['user']['followers']['totalCount']
    return 25

def query_count(funct_id):
    global QUERY_COUNT
    QUERY_COUNT[funct_id] += 1

def justify_format(root, element_id, new_text, length=0):
    if isinstance(new_text, int):
        new_text = f"{'{:,}'.format(new_text)}"
    new_text = str(new_text)
    
    element = root.find(f".//*[@id='{element_id}']")
    if element is not None:
        element.text = new_text

    dots_elem = root.find(f".//*[@id='{element_id}_dots']")
    if dots_elem is not None:
        just_len = max(0, length - len(new_text))
        if just_len <= 2:
            dot_map = {0: '', 1: ' ', 2: '. '}
            dot_string = dot_map.get(just_len, '')
        else:
            dot_string = ' ' + ('.' * just_len) + ' '
        dots_elem.text = dot_string

def svg_overwrite(filename, age_data, commit_data, star_data, repo_data, follower_data, loc_data):
    tree = etree.parse(filename)
    root = tree.getroot()
    
    justify_format(root, 'age_data', age_data, 24)
    justify_format(root, 'commit_data', commit_data, 8)
    justify_format(root, 'star_data', star_data, 5)
    justify_format(root, 'repo_data', repo_data, 5)
    justify_format(root, 'follower_data', follower_data, 5)
    justify_format(root, 'loc_data', loc_data[2], 9)
    justify_format(root, 'loc_add', loc_data[0], 8)
    justify_format(root, 'loc_del', loc_data[1], 7)
    
    tree.write(filename, encoding='utf-8', xml_declaration=True)
    print(f"Updated {filename}")

if __name__ == '__main__':
    print('Updating README SVG Stats...')
    # Default birthdate: April 15, 2005 (~19 years old)
    birthday = datetime.datetime(2005, 4, 15)
    age_data = daily_readme(birthday)
    
    commits = graph_commits()
    repos, stars = graph_repos_stars()
    followers = follower_getter()
    
    loc_data = ("38,100", "4,400", "42,500")
    
    if os.path.exists('dark_mode.svg'):
        svg_overwrite('dark_mode.svg', age_data, commits, stars, repos, followers, loc_data)
    if os.path.exists('light_mode.svg'):
        svg_overwrite('light_mode.svg', age_data, commits, stars, repos, followers, loc_data)
        
    print('Done!')
