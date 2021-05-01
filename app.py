from flask import Flask, render_template,  request, session, redirect, g, json
from flask_session import Session
from tempfile import mkdtemp
import re
import requests
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
    return render_template("tip.html")

