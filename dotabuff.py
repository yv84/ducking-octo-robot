import urllib.request
import json
import argparse
import re
import math
import threading


parser = argparse.ArgumentParser(
                   description=' http://dotabuff.com/ - Played with Me ')
parser.add_argument("--me", dest='my_players_id', type=int, required=True,
                   help='Id dotabuff')
parser.add_argument("--fp", dest='start_page', type=int, required=False,
                   default=0, help='first page matches')
parser.add_argument("--lp", dest='end_page', type=int, required=False,
                   default=0, help='last page matches')
parser.add_argument("--reload-m", dest='reloading_m', action='store_true',
                    help='reload matches')
parser.add_argument("--file", dest='outfile', type=str, required=False,
                   default='dotabuff.txt', help='save/load data from file')
parser.add_argument("--tp", dest='target_players', type=str, required=True,
                   help='list matching players')
parser.add_argument("--thr", dest='thread_count', type=int, required=False,
                   default=1, help='threads count')
parser.add_argument("--no-reload-p", dest='reloading_p', action='store_true',
                    help='skip reloading pages')
args = parser.parse_args()
my_players_id = args.my_players_id
start_page = args.start_page
end_page = args.end_page

if args.reloading_m:
    reloading_m = True
else:
    reloading_m = False


outfile = args.outfile
target_players = args.target_players
thread_count = args.thread_count

if args.reloading_p:
    reloading_p = False
else:
    reloading_p = True


while target_players.find('  ') > 0:
    target_players.replace(' ')
target_players =  ({int(i) for i in target_players.split(' ') if i.isdigit()})

re_1 = re.compile(r'<a\shref="/matches/(\d+)"\sclass="matchid">')
re_2 = re.compile(r'''(?x)
<a\shref="/players/
(\d+)
">
''')

def regex_find(text, pattern):
    match = None
    for match in re.finditer(pattern, text):
        s = match.start()
        e = match.end()
        #print('Found "%s" at %d:%d' % (text[s:e], s, e))
        if match:
            #print(match.groups())
            yield match.groups()

class SetEncoder(json.JSONEncoder):
    """
    set->list, Set is not JSON serializable
    """
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

def matches_page(player, sheet):
    try:
        page = urllib.request.urlopen(
            "http://dotabuff.com/players/" +
            str(player) +
            "/matches?page="+str(sheet)
            ).read()
    except urllib.error.URLError as e:
        print(e.reason)
    yield page

def get_matchid_from_page(player, list_matches, sheet):
    if not list_matches:
        for page in matches_page(player, sheet):
            for i in regex_find(page.decode('latin-1'), re_1):
                yield int(i[0])
    else:
        for match in list_matches:
            yield match

def get_match_page(players, list_matches, player, sheet, reloading_m):
    for match_id in get_matchid_from_page(player, list_matches, sheet):
        if reloading_m and match_id in players[player]:
            yield match_id, b''
        else:
            try:
                page = urllib.request.urlopen(
                    "http://dotabuff.com/matches/" +
                    str(match_id)
                    ).read()
            except urllib.error.URLError as e:
                print(e.reason)
            yield match_id, page

def get_players_id_from_match_page(dict_players, list_matches, 
                                        player, sheet, reloading_m):
    for match_id, page in get_match_page(dict_players, list_matches, 
                                                player, sheet, reloading_m):
        if not reloading_m or not dict_players[player].get(match_id):
            dict_players[player][match_id] = set()
        for i in regex_find(page.decode('latin-1'), re_2):
            dict_players[player][match_id] |= ({int(i[0])})
        print("%i = %s" %(match_id, dict_players[player][match_id]))
    return dict_players

def parser_task(dict_players, list_matches, player, target_players, 
                                            start, end, reloading_m=1):
    for page in range(start, end):
        dict_players.update(get_players_id_from_match_page(dict_players,
                                    list_matches, player, page, reloading_m))

def page_range_for_thread(thr, first_page, last_page):
    if thr > (last_page - first_page):
       for i in range(first_page, last_page, 1):
           yield i, i+1
    else:
        step = math.ceil((last_page - first_page)/thr)
        x = first_page
        while x < last_page:
            x = x + step
            yield (x-step,
            x if (x <= last_page) else last_page)

class ParserTask(threading.Thread):
    """ParserTask"""
    def __init__(self, dict_players, list_matches, my_players_id,
                 target_players, start_page, end_page, reloading_m):
        threading.Thread.__init__ (self)
        self.dict_players = dict_players
        self.list_matches = list_matches
        self.my_players_id = my_players_id
        self.target_players = target_players
        self.start_page = start_page
        self.end_page = end_page
        self.reloading_m = not reloading_m

    def run(self):
        parser_task(self.dict_players, self.list_matches, self.my_players_id, 
            self.target_players, self.start_page, self.end_page, self.reloading_m)


def find_players_played_with_me(players):
    for player in players:
        print('\n\n--------------------------\n')
        for match in players[player]:
            if players[player][match] - ({player}) & target_players:
                print("me: %s ; match: %s ; player: %s" % (player, match,
                    players[player][match] - ({player}) & target_players))


#-----------------------------------------------------------
# main task

dict_players = {}
list_all_matches = []
dict_players[my_players_id] = {}
try:
    # load
    with open(outfile, 'r') as ofile:
        p = (json.loads(ofile.read()))   
        for k in p:
            dict_players[int(k)] = {}
            for i in p[k]:
                dict_players[int(k)][int(i)] = set(p[k][i])
            for match in p[k]:
                list_all_matches.append(int(match))
except IOError:
    print('File '+outfile+' doesnt exists.')
    
    
threads = []
if reloading_p and reloading_m:
    for i,j in page_range_for_thread(thread_count,start_page,end_page):
        thread = ParserTask(dict_players, [], 
                        my_players_id, target_players, i, j, reloading_m)
        thread.start()
        threads.append(thread)
if not reloading_p and reloading_m:
    for i,j in page_range_for_thread(thread_count,0,
                            len(list_all_matches)):
        thread = ParserTask(dict_players, list_all_matches[i:j], 
                my_players_id, target_players, 0, 1, reloading_m)
        thread.start()
        threads.append(thread)

if reloading_p and not reloading_m:
    for i,j in page_range_for_thread(thread_count,start_page,end_page):
        thread = ParserTask(dict_players, list_all_matches, 
                        my_players_id, target_players, i, j, reloading_m)
        thread.start()
        threads.append(thread)
if not reloading_p and not reloading_m:
    thread = ParserTask(dict_players, list_all_matches,
                    my_players_id, target_players, 0, 1, reloading_m)
    thread.start()
    threads.append(thread)
print('start task')

# wait for every thread will done
for thread in threads:
    thread.join()

find_players_played_with_me(dict_players)

# save
if start_page != end_page and dict_players:
    with open(outfile, 'w') as ofile:
        ofile.write(json.dumps(dict_players, cls=SetEncoder))