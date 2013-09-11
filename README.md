ducking-octo-robot
==================

dotabuff.com parser. "Played with Me"

usage: dotabuff.py [-h] --me MY_PLAYERS_ID [--fp START_PAGE] [--lp END_PAGE]
                   [--reload MODE] [--file OUTFILE] --tp TARGET_PLAYERS
                   [--thr THREAD_COUNT]

http://dotabuff.com/ - Played with Me

optional arguments:
  -h, --help           show this help message and exit
  --me MY_PLAYERS_ID   Id dotabuff
  --fp START_PAGE      first page matches
  --lp END_PAGE        last page matches
  --reload MODE        reload web page
  --file OUTFILE       save/load data from file
  --tp TARGET_PLAYERS  list matching players
  --thr THREAD_COUNT   threads count



Example: $python3 dotabuff.py --me 100702042 --fp 1 --lp 60 --tp "100702042 76482434 100702042"
