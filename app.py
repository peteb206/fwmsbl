import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template
app = Flask(__name__)

# Data
fields_df = pd.read_csv('data/fields.csv').fillna('')
leagues_df = pd.read_csv('data/leagues.csv')
teams_df = pd.read_csv('data/teams.csv')
games_df = pd.read_csv('data/games.csv')
announcements_df = pd.read_csv('data/announcements.csv')

# Utils
full_calendar_date_format = '%Y-%m-%dT%H:%M:%SZ'

def row_to_dict(row: pd.DataFrame) -> dict:
    list_of_dict = row.to_dict(orient = 'records')
    return list_of_dict[0] if len(list_of_dict) == 1 else dict()

# API
@app.route('/api/events', methods = ['GET'])
def events_api():
    league_id = request.args.get('league', type = int)
    team_id = request.args.get('team', type = int)
    start = request.args.get('start', type = str)
    end = request.args.get('end', type = str)
    df_filter = pd.Series([True for _ in range(len(games_df.index))])
    if league_id != None:
        # Filter by league
        df_filter = games_df['league'] == league_id
    if team_id != None:
        # Filter by team
        df_filter = df_filter & ((games_df['away'] == team_id) | (games_df['home'] == team_id))
    df = games_df[df_filter].copy()

    # Handle dates
    df['start'] = pd.to_datetime(df['start'])
    df['end'] = df['start'].apply(lambda start: start + timedelta(hours = 3)) # Games last 3 hours
    if (start != None) & (end != None):
        # Filter by date
        df_filter = df_filter & (df['start'] >= start) & (df['end'] <= end)
    df['start'] = df['start'].dt.strftime(full_calendar_date_format)
    df['end'] = df['end'].dt.strftime(full_calendar_date_format)

    # Get supplemental data
    df['field'] = df['field'].apply(lambda field: row_to_dict(fields_df[fields_df['id'] == field]))
    df['away'] = df['away'].apply(lambda away: row_to_dict(teams_df[teams_df['id'] == away]))
    df['home'] = df['home'].apply(lambda home: row_to_dict(teams_df[teams_df['id'] == home]))
    df['league'] = df['league'].apply(lambda league: row_to_dict(leagues_df[leagues_df['id'] == league]))
    df['color'] = df['league'].apply(lambda league: league['color'])
    df['title'] = df.apply(lambda row: f'{row["league"]["name"] + " - " if league_id == None else ""}{row["away"]["name"]} @ {row["home"]["name"]} ({row["field"]["name"]})', axis = 1) if len(df.index) > 0 else ''
    return jsonify(df.to_dict(orient = 'records'))

@app.route('/api/leagues', methods = ['GET'])
def leagues_api():
    league_id = request.args.get('id', type = int)
    league_name = request.args.get('name', type = str)
    df_filter = pd.Series([True for _ in range(len(leagues_df.index))])
    if league_id != None:
        # Filter by id
        df_filter = leagues_df['id'] == league_id
    if league_name != None:
        # Filter by name
        df_filter = df_filter & (leagues_df['name'] == league_name)
    df = leagues_df[df_filter].copy()
    return jsonify(df.to_dict(orient = 'records'))

@app.route('/api/fields', methods = ['GET'])
def fields_api():
    field_id = request.args.get('id', type = int)
    field_name = request.args.get('name', type = str)
    df_filter = pd.Series([True for _ in range(len(fields_df.index))])
    if field_id != None:
        # Filter by id
        df_filter = leagues_df['id'] == field_id
    if field_name != None:
        # Filter by name
        df_filter = df_filter & (leagues_df['name'] == field_name)
    df = fields_df[df_filter].copy()
    df['link'] = df.apply(lambda row: f'http://www.google.com/maps/place/{row["latitude"]},{row["longitude"]}', axis = 1)
    return jsonify(df.to_dict(orient = 'records'))

@app.route('/api/teams', methods = ['GET'])
def teams_api():
    team_id = request.args.get('id', type = int)
    league_id = request.args.get('league', type = int)
    team_name = request.args.get('name', type = str)
    df_filter = pd.Series([True for _ in range(len(teams_df.index))])
    if team_id != None:
        # Filter by id
        df_filter = teams_df['id'] == team_id
    if league_id != None:
        # Filter by league
        df_filter = df_filter & (teams_df['league'] == league_id)
    if team_name != None:
        # Filter by name
        df_filter = df_filter & (teams_df['name'] == team_name)
    df = teams_df[df_filter].copy()
    df['league'] = df['league'].apply(lambda league: row_to_dict(leagues_df[leagues_df['id'] == league]))
    return jsonify(df.to_dict(orient = 'records'))

@app.route('/api/announcements', methods = ['GET'])
def announcements_api():
    df = announcements_df.rename({'datetime': 'start', 'message': 'title'}, axis = 1)
    df['start'].fillna(datetime.now().strftime(full_calendar_date_format), inplace = True)
    return jsonify(df.to_dict(orient = 'records'))

# HTML
@app.route('/schedule', methods = ['GET'])
def schedule():
    return render_template('schedule.html')

@app.route('/roster', methods = ['GET'])
def roster():
    return render_template('roster.html')

@app.route('/rules', methods = ['GET'])
def rules():
    return render_template('rules.html')

@app.route('/fields', methods = ['GET'])
def fields():
    return render_template('fields.html')

@app.route('/waiver', methods = ['GET'])
def waiver():
    return render_template('waiver.html')

@app.route('/', methods = ['GET'])
def home():
    return render_template('home.html')