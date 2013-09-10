import urllib.request
import json
import argparse
import re


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

def get_match_page(player, sheet, mode):
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

def get_players_id_from_match_page(player, sheet, mode):
    for match_id, page in get_match_page(player, sheet, mode):
        if not mode or not players[player].get(match_id):
            players[player][match_id] = set()
        for i in regex_find(page.decode('latin-1'), re_2):
            players[player][match_id] |= ({int(i[0])})
        print("%i = %s" %(match_id, players[player][match_id]))
    return players[player]

def main(player,  target_players, start, end, mode=1):
    for page in range(start, end):
        get_players_id_from_match_page(player, page, mode)
    for player in players:
        print('\n\n--------------------------\n')
        for match in players[player]:
            if players[player][match] - ({player}) & target_players:
                print("me: %s ; match: %s ; player: %s" % (player, match,
                    players[player][match] - ({player}) & target_players))

#--------------------------------------------------------------------

try:
    # load
    with open(outfile, 'r') as ofile:
        p = (json.loads(ofile.read()))
        players = {}
        for k in p:
            players[int(k)] = {}
            for i in p[k]:
                players[int(k)][int(i)] = set(p[k][i])
except IOError:
    print('File '+outfile+' doesnt exists.')
    players = {}
    players[my_players_id] = {}

main(my_players_id, target_players, start_page, end_page, mode)

# save
if start_page != end_page and players:
    with open(outfile, 'w') as ofile:
        ofile.write(json.dumps(players, cls=SetEncoder))

