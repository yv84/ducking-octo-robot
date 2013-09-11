import urllib.request
import json
import argparse
import re
import math
import threading


parser = argparse.ArgumentParser(description=' http://dotabuff.com/  ')
parser.add_argument("--me", dest='my_players_id', type=int, required=True,
                   help='Id dotabuff')
parser.add_argument("--fp", dest='start_page', type=int, required=False,
                   default=0, help='first page matches')
parser.add_argument("--lp", dest='end_page', type=int, required=False,
                   default=0, help='last page matches')
parser.add_argument("--reload", dest='mode', type=str, required=False,
                   default='no', help='reload web page')
parser.add_argument("--file", dest='outfile', type=str, required=False,
                   default='dotabuff.txt', help='save/load data from file')
parser.add_argument("--tp", dest='target_players', type=str, required=True,
                   help='list matching players')
parser.add_argument("--thr", dest='thread_count', type=int, required=False,
                   default=1, help='threads count')
args = parser.parse_args()
my_players_id = args.my_players_id
start_page = args.start_page
end_page = args.end_page
if args.mode and args.mode.lower() in ('y', 'yes'):
    mode = 0
else:
    mode = 1

outfile = args.outfile
target_players = args.target_players
thread_count = args.thread_count

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

def get_matchid_from_page(player, sheet):
    for page in matches_page(player, sheet):
        for i in regex_find(page.decode('latin-1'), re_1):
            yield int(i[0])

def get_match_page(players, player, sheet, mode):
    for match_id in get_matchid_from_page(player, sheet):
        if mode and match_id in players[player]:
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

def get_players_id_from_match_page(dict_players, player, sheet, mode):
    for match_id, page in get_match_page(dict_players, player, sheet, mode):
        if not mode or not dict_players[player].get(match_id):
            dict_players[player][match_id] = set()
        for i in regex_find(page.decode('latin-1'), re_2):
            dict_players[player][match_id] |= ({int(i[0])})
        print("%i = %s" %(match_id, dict_players[player][match_id]))
    return dict_players

def parser_task(dict_players, player, target_players, start, end, mode=1):
    for page in range(start, end):
        dict_players.update(get_players_id_from_match_page(dict_players,
                                                    player, page, mode))

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
    def __init__(self, dict_players, my_players_id,
                 target_players, start_page, end_page, mode):
        threading.Thread.__init__ (self)
        self.dict_players = dict_players
        self.my_players_id = my_players_id
        self.target_players = target_players
        self.start_page = start_page
        self.end_page = end_page
        self.mode = mode

    def run(self):
        parser_task(self.dict_players, self.my_players_id, self.target_players,
             self.start_page, self.end_page, self.mode)


def find_players_played_with_me(players):
    for player in players:
        print('\n\n--------------------------\n')
        for match in players[player]:
            if players[player][match] - ({player}) & target_players:
                print("me: %s ; match: %s ; player: %s" % (player, match,
                    players[player][match] - ({player}) & target_players))


#-----------------------------------------------------------
# main task

try:
    # load
    with open(outfile, 'r') as ofile:
        p = (json.loads(ofile.read()))
        dict_players = {}
        for k in p:
            dict_players[int(k)] = {}
            for i in p[k]:
                dict_players[int(k)][int(i)] = set(p[k][i])
except IOError:
    print('File '+outfile+' doesnt exists.')
    dict_players = {}
    dict_players[my_players_id] = {}


threads = []
for i,j in page_range_for_thread(thread_count,start_page,end_page):
    thread = ParserTask(dict_players, my_players_id, target_players, i, j, mode)
    thread.start()
    threads.append(thread)

# wait for every thread will done
for thread in threads:
    thread.join()

find_players_played_with_me(dict_players)

# save
if start_page != end_page and dict_players:
    with open(outfile, 'w') as ofile:
        ofile.write(json.dumps(dict_players, cls=SetEncoder))
