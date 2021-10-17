from flask import Flask, render_template, request, session, redirect
from flask_session import Session
from tempfile import mkdtemp
import requests
import time
from dotenv import load_dotenv
import os
from helpers import login_required, format_pcnt

load_dotenv()

app = Flask(__name__)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.filters["formatpcnt"] = format_pcnt

restEndpoint = os.environ.get('TIPPER_BACKEND_ENDPOINT')
tipperMLEP = os.environ.get('TIPPER_ML_ENDPOINT')

TEAMMAP = {
    'Brisbane Lions': 'brisbanel',
    'Hawthorn Hawks': 'hawthorn',
    'Collingwood Magpies': 'collingwood',
    'Fremantle Dockers': 'fremantle',
    'Carlton Blues': 'carlton',
    'Essendon Bombers': 'essendon',
    'Geelong Cats': 'geelong',
    'Sydney Swans': 'swans',
    'Greater Western Sydney Giants': 'gws',
    'Gold Coast Suns': 'goldcoast',
    'Adelaide Crows': 'adelaide',
    'Melbourne Demons': 'melbourne',
    'Richmond Tigers': 'richmond',
    'North Melbourne Kangaroos': 'kangaroos',
    'St Kilda Saints': 'stkilda',
    'Port Adelaide Power': 'padelaide',
    'Western Bulldogs': 'bullldogs',
    'West Coast Eagles': 'westcoast'
}


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


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    # otherwise post login details
    error = ''
    username = request.form.get('username')
    password = request.form.get('password')

    if not username:
        error = 'username not provided'
        return render_template('login.html', error=error)
    if not password:
        error = 'password not provided'
        return render_template('login.html', error=error)
    # call signin endpoint on rest api
    res = requests.post(f'{restEndpoint}/signin', data={'email': username, 'password': password}).json()

    if "id" in res:
        session["user_id"] = res['id']
        return redirect('/')
    else:
        error = res['msg']
    # if creds invalid, redirect to login with GET and error message
    return render_template('login.html', error=error)


@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect('/')


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get('username')
    password = request.form.get('password')
    re_password = request.form.get('repassword')
    if not username:
        return render_template('register.html', error="username not provided")
    if not password:
        return render_template('register.html', error="password not provided")
    if not re_password:
        return render_template('register.html', error="repassword not provided")
    if not password == re_password:
        return render_template('register.html', error="passwords dont match")

    # call register endpoint on rest api
    res = requests.post(f'{restEndpoint}/register', data={'email': username, 'password': password}).json()

    if "id" in res:
        session["user_id"] = res['id']
        return redirect('/')
    else:
        error = res['msg']
    # if creds invalid, redirect to login with GET and error message
    return render_template('register.html', error=error)


# list of teams. can sort as ladder, can drill down to view their games / stats
@app.route('/ladder', methods=['GET', 'POST'])
@login_required
def ladder():
    season = request.form.get('season')
    # default season to 2020
    if not season:
        season = '2021'

    teams = requests.get(f'{restEndpoint}/teams').json()
    ladder = requests.get(f'{restEndpoint}/ladder/{season}').json()

    for team in ladder:
        # look for team_identifier
        detail = next((x for x in teams if x['team_identifier'] == team['teamname']), None)
        team['fullname'] = f"{detail['city']} {detail['name']}"
    return render_template('ladder.html', ladder=ladder, season=season)


@app.route('/teamdetail', methods=['GET', 'POST'])
@login_required
def teamdetail():
    # team is required for teamdetail. 
    if request.method == 'GET':
        team = request.args.get('team')
    else:
        team = request.form.get('team')
    if not team:
        teams = requests.get(f'{restEndpoint}/teams').json()
        return render_template("teamdetail.html", teamslist=teams)

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

    # get raw data for chart
    pcnt_diff_stats = requests.post(f'{restEndpoint}/pcntDiff/',
                                    data={'team': team, 'yearStart': 2020, 'yearEnd': 2020}).json()
    available_stats = [item for item in list(pcnt_diff_stats[0].keys()) if item not in [
        'team_id', 'opponent', 'year', 'round'
    ]]

    selected_stats = request.form.getlist('stat')
    if not selected_stats:
        # default selected stats
        selected_stats = ['disposals']

    # populate data for chart
    data = []
    for stat in selected_stats:
        series = {
            'type': "line",
            'name': stat,
            'showInLegend': True,
            'markerSize': 0,
            'dataPoints': []
        }
        for round_number in pcnt_diff_stats:
            series['dataPoints'].append({'x': round_number['round'], 'y': round_number[stat]})
        data.append(series)

    # to remember location on page when looking at stats
    scroll_pos = ""
    scroll_pos = request.form.get("scrollPos")
    return render_template("teamdetail.html",
                           team=team, games=games, pcntdiffs=data,
                           availablestats=available_stats, selectedstats=selected_stats,
                           scrollPos=scroll_pos
                           )


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

    odds = requests.get(f'{restEndpoint}/oddsNextWeek').json()
    game_list = []
    for game in odds:
        game_dict = {'id': game['id'], 'team1': game['teams'][0], 'team2': game['teams'][1],
                     'commence_time': time.strftime('%A %d %B %Y %H:%M:%S', time.localtime(game['commence_time']))}
        game_list.append(game_dict)

    selected_game_id = request.args.get('game')
    selected_game = next((x for x in odds if x['id'] == selected_game_id), None)
    if selected_game:
        for site in selected_game['sites']:
            site.update(last_update=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(site['last_update'])))

        team_ids = [
            TEAMMAP[selected_game['teams'][0]],
            TEAMMAP[selected_game['teams'][1]]
        ]
        selected_game.update(teamIds=team_ids)

        try:
            prediction = requests.get(
                f'{tipperMLEP}/predict/linearregression_pcntdiffstats/{team_ids[0]}/{team_ids[1]}/weighted/0.2').json()
            print(prediction)
            tipper_score = [prediction['team1score'], prediction['team2score']]
            team_scores = ["{:.3f}".format(tipper_score[0]), "{:.3f}".format(tipper_score[1])]
            selected_game.update(teamscores=team_scores)
        except:
            return render_template('failure.html', text='could not fetch prediction')

    return render_template("tip.html", selectedGame=selected_game, gameList=game_list, odds=odds)
