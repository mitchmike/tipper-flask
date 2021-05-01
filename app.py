from flask import Flask, render_template,  request, session, redirect, g, json
from flask_session import Session
from tempfile import mkdtemp
import re
import requests
import time
import random
from dotenv import load_dotenv
import os
from helpers import login_required, formatpcnt

load_dotenv()

app = Flask(__name__)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.filters["formatpcnt"] = formatpcnt

restEndpoint = os.environ.get('REST_ENDPOINT')



TEAMMAP = {
  'Brisbane Lions':'brisbanel',
  'Hawthorn Hawks':'hawthorn',
  'Collingwood Magpies':'collingwood',
  'Fremantle Dockers':'fremantle',
  'Carlton Blues':'carlton',
  'Essendon Bombers':'essendon',
  'Geelong Cats':'geelong',
  'Sydney Swans':'swans',
  'Greater Western Sydney Giants':'gws',
  'Gold Coast Suns':'goldcoast',
  'Adelaide Crows':'adelaide',
  'Melbourne Demons':'melbourne',
  'Richmond Tigers':'richmond',
  'North Melbourne Kangaroos':'kangaroos',
  'St Kilda Saints':'stkilda',
  'Port Adelaide Power':'padelaide',
  'Western Bulldogs':'bullldogs',
  'West Coast Eagles':'westcoast'
};




# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# about tipper
@app.route('/')
@login_required
def index():
    return render_template("index.html")


@app.route('/login', methods=["GET","POST"])
def login():
    if request.method=="GET":
        return render_template("login.html")
    # otherwise post login details
    error=''
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username:
        error='username not provided'
        return render_template('login.html',error=error)
    if not password:
        error='password not provided'
        return render_template('login.html',error=error)
    
    #call signin endpoint on rest api
    res = requests.post(f'{restEndpoint}/signin',data={'email':username,'password':password}).json()

    if "id" in res:
        session["user_id"] = res['id']
        return redirect('/')
    else:
        error=res['msg']
    # if creds invalid, redirect to login with GET and error message
    return render_template('login.html', error=error)
    
@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect('/')

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method=="GET":
        return render_template("register.html")

    username = request.form.get('username')
    password = request.form.get('password')
    repassword = request.form.get('repassword')
    if not username:
        return render_template('register.html',error="username not provided")
    if not password:
        return render_template('register.html',error="password not provided")
    if not repassword:
        return render_template('register.html',error="repassword not provided")
    if not password == repassword:
        return render_template('register.html',error="passwords dont match")

    #call register endpoint on rest api
    res = requests.post(f'{restEndpoint}/register',data={'email':username,'password':password}).json()
    
    if "id" in res:
        session["user_id"] = res['id']
        return redirect('/')
    else:
        error=res['msg']
    # if creds invalid, redirect to login with GET and error message
    return render_template('register.html', error=error)

    

# list of teams. can sort as ladder, can drill down to view their games / stats
@app.route('/ladder', methods=['GET','POST'])
@login_required
def ladder():
    
    season = request.form.get('season')
    #default season to 2020
    if not season:
        season = '2020'
        
    teams = requests.get(f'{restEndpoint}/teams').json()
    ladder = requests.get(f'{restEndpoint}/ladder/{season}').json()

    for team in ladder:
        #look for team_identifier
        detail = next((x for x in teams if x['team_identifier'] == team['teamname']),None)
        team['fullname'] = f"{detail['city']} {detail['name']}"
    return render_template('ladder.html',ladder=ladder, season=season)



@app.route('/teamdetail',methods=['GET','POST'])
@login_required
def teamdetail():
    
    
    # team is required for teamdetail. 
    if request.method=='GET':
        team = request.args.get('team')
    else:
        team = request.form.get('team')
    if not team:
        teams = requests.get(f'{restEndpoint}/teams').json()
        return render_template("teamdetail.html",teamslist=teams)

    # recent games data
    games = requests.get(f'{restEndpoint}/games/byyearandteam/{team}/2020').json()
    games = [item for item in games if item['round'].isnumeric()]
    games = sorted(games, key=lambda i: int(i['round']), reverse=True)
    games = games[:10]
    for game in games:
        if game['for'] > game['against']:
            winner = game['team']
        elif game['for'] == game['against']:
            winner = 'Draw'
        else:
            winner = game['opponent']
        game['winner'] = winner
    
    # chart
    # get raw data for chart
    pcntdiffStats = requests.post(f'{restEndpoint}/pcntDiff/',data={'team':team, 'yearStart':2020,'yearEnd':2020}).json()
    availablestats = [item for item in list(pcntdiffStats[0].keys()) if item not in [
        'team_id','opponent','year','round'
        ]]

    selectedstats=request.form.getlist('stat')
    if not selectedstats:
        #default selected stats
        selectedstats=['disposals']

    # populate data for chart
    data=[]
    for stat in selectedstats:
        disposals=[]
        series = {
            'type':"line",
            'name': stat,
            'showInLegend': True,
            'markerSize': 0,
            'dataPoints':[]
        }
        for round in pcntdiffStats:
            series['dataPoints'].append({'x':round['round'], 'y':round[stat]})
        data.append(series)

    # to remember location on page when looking at stats
    scrollPos = ""
    scrollPos = request.form.get("scrollPos")
    return render_template("teamdetail.html", 
                            team=team,games=games,pcntdiffs=data,
                            availablestats=availablestats,selectedstats=selectedstats,
                            scrollPos=scrollPos
                        )

    


# source odds from betting companies and also a random number generator for the probability of winning for a team -> give a tipscore/value score based on that
@app.route('/tip')
@login_required
def tip():
    
    # TODO: select other rounds and get odds for those
    # if request.method == 'GET':
    #     selectedSeason = request.args.get('selectedSeason')
    #     if not selectedSeason:
    #         selectedSeason='2021'
    #     selectedRound=7
    #     return render_template('tip.html', selectedSeason=selectedSeason, selectedRound=selectedRound)


    # deactivated for testing/dev so i dont use all allocated requests
    # odds = requests.get(f'{restEndpoint}/oddsNextWeek').json()


    odds=[{'id': 'f6584a8eaefa10f6349fc2514991a757', 'sport_key': 'aussierules_afl', 'sport_nice': 'AFL', 'teams': ['Melbourne Demons', 'North Melbourne Kangaroos'], 'commence_time': 1619925000, 'home_team': 'North Melbourne Kangaroos', 'sites': [{'site_key': 'sportsbet', 'site_nice': 'SportsBet', 'last_update': 1619907068, 'odds': {'h2h': [1.02, 13]}}, {'site_key': 'tab', 'site_nice': 'TAB', 'last_update': 1619906851, 'odds': {'h2h': [1.01, 14]}}, {'site_key': 'betfair', 'site_nice': 'Betfair', 'last_update': 1619906852, 'odds': {'h2h': [1.05, 17.5], 'h2h_lay': [1.06, 19]}}, {'site_key': 'ladbrokes', 'site_nice': 'Ladbrokes', 'last_update': 1619906852, 'odds': {'h2h': [1.02, 15]}}, {'site_key': 'neds', 'site_nice': 'Neds', 'last_update': 1619906852, 'odds': {'h2h': [1.02, 15]}}, {'site_key': 'pointsbetau', 'site_nice': 'PointsBet (AU)', 'last_update': 1619907087, 'odds': {'h2h': [1.01, 17]}}, {'site_key': 'unibet', 'site_nice': 'Unibet', 'last_update': 1619906852, 'odds': {'h2h': [1.01, 14]}}], 'sites_count': 7}, {'id': 'b98fd17b96a8109ec312e46f57c98c9a', 'sport_key': 'aussierules_afl', 'sport_nice': 'AFL', 'teams': ['Carlton Blues', 'Essendon Bombers'], 'commence_time': 1619932800, 'home_team': 'Essendon Bombers', 'sites': [{'site_key': 'sportsbet', 'site_nice': 'SportsBet', 'last_update': 1619907068, 'odds': {'h2h': [1.81, 2.04]}}, {'site_key': 'tab', 'site_nice': 'TAB', 'last_update': 1619906851, 'odds': {'h2h': [1.77, 2.05]}}, {'site_key': 'betfair', 'site_nice': 'Betfair', 'last_update': 1619906852, 'odds': {'h2h': [1.84, 2.16], 'h2h_lay': [1.85, 2.18]}}, {'site_key': 'ladbrokes', 'site_nice': 'Ladbrokes', 'last_update': 1619906852, 'odds': {'h2h': [1.75, 2.1]}}, {'site_key': 'neds', 'site_nice': 'Neds', 'last_update': 1619906852, 'odds': {'h2h': [1.75, 2.1]}}, {'site_key': 'pointsbetau', 'site_nice': 'PointsBet (AU)', 'last_update': 1619907087, 'odds': {'h2h': [1.77, 2.05]}}, {'site_key': 'unibet', 'site_nice': 'Unibet', 'last_update': 1619906852, 'odds': {'h2h': [1.77, 2.06]}}], 'sites_count': 7}, {'id': '8ba3aab2aba5f3e312675a074673d044', 'sport_key': 'aussierules_afl', 'sport_nice': 'AFL', 'teams': ['Fremantle Dockers', 'West Coast Eagles'], 'commence_time': 1619937600, 'home_team': 'West Coast Eagles', 'sites': [{'site_key': 'unibet', 'site_nice': 'Unibet', 'last_update': 1619906852, 'odds': {'h2h': [1.96, 1.84]}}, {'site_key': 'ladbrokes', 'site_nice': 'Ladbrokes', 'last_update': 1619906852, 'odds': {'h2h': [2.05, 1.77]}}, {'site_key': 'neds', 'site_nice': 'Neds', 'last_update': 1619906852, 'odds': {'h2h': [2.05, 1.77]}}, {'site_key': 'betfair', 'site_nice': 'Betfair', 'last_update': 1619906852, 'odds': {'h2h': [2.04, 1.95], 'h2h_lay': [2.06, 1.96]}}, {'site_key': 'tab', 'site_nice': 'TAB', 'last_update': 1619906851, 'odds': {'h2h': [2, 1.8]}}, {'site_key': 'sportsbet', 'site_nice': 'SportsBet', 'last_update': 1619907068, 'odds': {'h2h': [2.05, 1.8]}}, {'site_key': 'pointsbetau', 'site_nice': 'PointsBet (AU)', 'last_update': 1619907087, 'odds': {'h2h': [1.95, 1.85]}}], 'sites_count': 7}]
    print(odds)
    gameList=[]
    for game in odds:
        gameDict={'id':game['id'],
                'team1':game['teams'][0],
                'team2':game['teams'][1]}
        gameDict['commence_time'] = time.strftime('%A %d %B %Y %H:%M:%S', time.localtime(game['commence_time']))
        gameList.append(gameDict)

    print(gameList)

    selectedGameID = request.args.get('game')
    selectedGame = next((x for x in odds if x['id'] == selectedGameID),None)
    if selectedGame:     
        for site in selectedGame['sites']:
            site.update(last_update=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(site['last_update'])))

        tipperScore = random.random()
        teamscores=[tipperScore,1-tipperScore]
        selectedGame.update(teamscores=teamscores)

        teamIds=[
            TEAMMAP[selectedGame['teams'][0]],
            TEAMMAP[selectedGame['teams'][1]]
        ]
        selectedGame.update(teamIds=teamIds)

        print(selectedGame)


    return render_template("tip.html",selectedGame=selectedGame,gameList=gameList,odds=odds)

