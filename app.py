from flask import Flask, render_template
import query

app = Flask(__name__)

# Utils
full_calendar_date_format = '%Y-%m-%dT%H:%M:%SZ'

def format_game_result(game_data: dict) -> str:
    if ('team1' not in game_data.keys()) | ('team2' not in game_data.keys()):
        return ''
    elif (game_data['team1']['_id'] == None) | (game_data['team2']['_id'] == None):
        return ''
    elif ('team1_score' not in game_data.keys()) | ('team2_score' not in game_data.keys()):
        if game_data['team1']['_id'] == game_data['home']['_id']:
            return ' @ '.join([game_data['team2']['name'], game_data['team1']['name']])
        elif  game_data['team2']['_id'] == game_data['home']['_id']:
            return ' @ '.join([game_data['team1']['name'], game_data['team2']['name']])
        else: # No home team specified
            return ' vs. '.join([game_data['team1']['name'], game_data['team2']['name']])
    elif int(game_data['team2_score']) > int(game_data['team1_score']):
        return f'{game_data["team2"]["name"]} beat {game_data["team1"]["name"]} {game_data["team2_score"]}-{game_data["team1_score"]}'
    elif int(game_data['team2_score']) < int(game_data['team1_score']):
        return f'{game_data["team1"]["name"]} beat {game_data["team2"]["name"]} {game_data["team1_score"]}-{game_data["team2_score"]}'
    else:
        return f'{game_data["team1"]["name"]} tied {game_data["team2"]["name"]} {game_data["team1_score"]}-{game_data["team2_score"]}'

def events():
    games = query.games()
    practices = query.practices()
    events = list()
    for event in (games + practices):
        event['start'] = event['start'].strftime(full_calendar_date_format)
        event['end'] = event['end'].strftime(full_calendar_date_format)
        if event['type'] == 'game':
            event['title'] = format_game_result(event)
        elif event['team']['_id'] != None:
            event['title'] = f'{event["team"]["name"]} Practice'
        else:
            event['title'] = 'Open Practice Slot'
        if 'color' in event['league'].keys():
            event['backgroundColor'] = event['league']['color']
        events.append(event)
    return events

def standings():
    games = query.games()
    teams = query.teams()
    leagues = list()
    for league in query.leagues():
        league['teams'] = list()
        for team in filter(lambda team: team['league']['_id'] == league['_id'], teams):
            team['W'] = 0
            team['L'] = 0
            team['T'] = 0
            team['winPct'] = 0
            league['teams'].append(team)
        league_completed_games = filter(lambda game: (game['league']['_id'] == league['_id']) & ('team1_score' in game.keys()) & ('team2_score' in game.keys()), games)
        for completed_game in league_completed_games:
            team1_index = next((index for index, d in enumerate(league['teams']) if d['_id'] == completed_game['team1']['_id']), None)
            team2_index = next((index for index, d in enumerate(league['teams']) if d['_id'] == completed_game['team2']['_id']), None)
            if completed_game['team1_score'] > completed_game['team2_score']:
                league['teams'][team1_index]['W'] += 1
                league['teams'][team2_index]['L'] += 1
            elif completed_game['team1_score'] < completed_game['team2_score']:
                league['teams'][team1_index]['L'] += 1
                league['teams'][team2_index]['W'] += 1
            else:
                league['teams'][team1_index]['T'] += 1
                league['teams'][team2_index]['T'] += 1
            for team_index in [team1_index, team2_index]:
                league['teams'][team_index]['winPct'] = (league['teams'][team_index]['W'] + 0.5 * league['teams'][team_index]['T']) / (league['teams'][team_index]['W'] + league['teams'][team_index]['L'] + league['teams'][team_index]['T'])
        league['teams'] = sorted(league['teams'], key = lambda t: (-t['winPct'], -t['W'], -t['T'], t['L'], t['name']))
        [team.update({"winPct": '{:.3f}'.format(round(team['winPct'], 3)).replace('0.', '.')}) for team in league['teams']]
        leagues.append(league)
    return leagues

# HTML
@app.route('/schedule', methods = ['GET'])
def schedule():
    return render_template('schedule.html', leagues = query.leagues(), teams = query.teams(), events = events())

@app.route('/roster', methods = ['GET'])
def roster():
    return render_template('roster.html')

@app.route('/rules', methods = ['GET'])
def rules():
    return render_template('rules.html')

@app.route('/fields', methods = ['GET'])
def fields():
    fields = list()
    for field in query.fields():
        field['link'] = f'https://www.google.com/maps/place/{field["latitude"]},{field["longitude"]}'
        fields.append(field)
    return render_template('fields.html', fields = fields)

@app.route('/sponsors', methods = ['GET'])
def sponsors():
    return render_template('sponsors.html', sponsors = query.sponsors())

@app.route('/', methods = ['GET'])
def home():
    return render_template('home.html', leagues = query.leagues(), events = events(), standings = standings())
