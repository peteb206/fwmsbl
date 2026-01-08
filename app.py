import pandas as pd
from datetime import datetime, timedelta
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, jsonify, request, render_template, redirect

app = Flask(__name__)

# Data
def refresh_data() -> dict[str, gspread.Worksheet]:
    print('Attempting to refresh app data')
    client: gspread.Client = gspread.authorize(
        ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(os.environ['GOOGLE_CLOUD_API_KEY']),
            [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
        )
    )
    google_sheet = client.open_by_key('1BAJkmcYC_WtqZHU2UTXuHCOQGMOMYBrTOXBosSLNeTo')
    worksheet_dict = {
        'leagues': google_sheet.get_worksheet_by_id(1586626557),
        'teams': google_sheet.get_worksheet_by_id(931255258),
        'games': google_sheet.get_worksheet_by_id(1416711061),
        'fields': google_sheet.get_worksheet_by_id(1923145408),
        'sponsors': google_sheet.get_worksheet_by_id(377416456)
    }
    print('Successfully refreshed app data')
    return worksheet_dict

def get_df(from_sheet: str) -> pd.DataFrame:
    global app_data
    df = pd.DataFrame()
    try:
        df = pd.DataFrame(app_data[from_sheet].get_all_records())
    except Exception as e:
        print(e)
        try:
            app_data = refresh_data()
            df = pd.DataFrame(app_data[from_sheet].get_all_records())
        except: 
            print('Could not get data from the Google Sheet')
    return df

# Utils
full_calendar_date_format = '%Y-%m-%dT%H:%M:%SZ'

def row_to_dict(row: pd.DataFrame) -> dict:
    list_of_dict = row.to_dict(orient = 'records')
    return list_of_dict[0] if len(list_of_dict) == 1 else dict()

def format_game_result(game_data: pd.Series) -> str:
    if (game_data['team1_score'] in ['', None]) | (game_data['team2_score'] in ['', None]):
        if game_data['team1'] == game_data['home']:
            return ' @ '.join([game_data["team2"], game_data["team1"]])
        elif  game_data['team2'] == game_data['home']:
            return ' @ '.join([game_data["team1"], game_data["team2"]])
        else: # No home team specified
            return ' vs. '.join([game_data["team1"], game_data["team2"]])
    elif int(game_data['team2_score']) > int(game_data['team1_score']):
        return f'{game_data["team2"]} beat {game_data["team1"]} {game_data["team2_score"]}-{game_data["team1_score"]}'
    elif int(game_data['team2_score']) < int(game_data['team1_score']):
        return f'{game_data["team1"]} beat {game_data["team2"]} {game_data["team1_score"]}-{game_data["team2_score"]}'
    else:
        return f'{game_data["team1"]} tied {game_data["team2"]} {game_data["team1_score"]}-{game_data["team2_score"]}'

# API
def events():
    df = get_df('games')
    df['start'] = pd.to_datetime(df['start'])
    df['end'] = df['start'].apply(lambda start: start + timedelta(hours = 3)) # Games last 3 hours
    df['start'] = df['start'].dt.strftime(full_calendar_date_format)
    df['end'] = df['end'].dt.strftime(full_calendar_date_format)
    df = df.merge(get_df('fields').rename({'name': 'field'}, axis = 1), how = 'left', on = 'field')
    df = df.merge(get_df('leagues').rename({'name': 'league'}, axis = 1), how = 'left', on = 'league')
    df['title'] = df.apply(lambda row: format_game_result(row), axis = 1) if len(df.index) > 0 else ''
    return df.fillna('').query('(team1 != "") | (team2 != "")').to_dict(orient = 'records')

def leagues() -> list[dict]:
    return get_df('leagues').to_dict(orient = 'records')

def teams() -> list[dict]:
    return get_df('teams').to_dict(orient = 'records')

def standings():
    standings = dict()
    games_df, leagues_df, teams_df = get_df('games'), get_df('leagues'), get_df('teams')
    for league_dict in leagues_df.to_dict(orient = 'records'):
        league = league_dict['name']
        df = games_df[(games_df['team1_score'] != '') & (games_df['team2_score'] != '') & (games_df['league'] == league)].copy()
        league_teams_df = teams_df[teams_df['league'] == league]
        standings_df, wlt = None, ['W', 'L', 'T']
        if len(df.index) == 0:
            standings_df = league_teams_df.drop('league', axis = 1)
            standings_df[wlt] = 0
            standings_df['winPct'] = '.000'
        else:
            df['team1_result'] = df.apply(lambda row: 'T' if row['team1_score'] == row['team2_score'] else 'W' if int(row['team1_score']) > int(row['team2_score']) else 'L', axis = 1)
            df['team2_result'] = df['team1_result'].apply(lambda x: 'T' if x == 'T' else 'W' if x == 'L' else 'L')
            away_home_df = pd.concat([
                df.groupby(side)[f'{side}_result'].value_counts().unstack() for side in ['team1', 'team2']
            ]).reset_index().rename({'index': 'name'}, axis = 1)
            for col in wlt:
                if col not in away_home_df.columns:
                    away_home_df[col] = 0
            results_df = away_home_df.groupby('name')[wlt].sum()
            results_df['winPct'] = results_df.apply(lambda row: '{:.3f}'.format((row['W'] + row['T'] / 2) / row.sum()).lstrip('0'), axis = 1)

            standings_df = league_teams_df.merge(results_df.reset_index(), how = 'left', on = 'name').drop('league', axis = 1).sort_values(by = 'winPct', ascending = False)
        standings[league] = standings_df.fillna(0).astype({'W': int, 'L': int, 'T': int}).to_dict(orient = 'records')
    return standings

# HTML
@app.route('/schedule', methods = ['GET'])
def schedule():
    return render_template('schedule.html', leagues = leagues(), teams = teams(), events = events())

@app.route('/roster', methods = ['GET'])
def roster():
    return render_template('roster.html')

@app.route('/rules', methods = ['GET'])
def rules():
    return render_template('rules.html')

@app.route('/fields', methods = ['GET'])
def fields():
    df = get_df('fields')
    df['link'] = df.apply(lambda row: f'https://www.google.com/maps/place/{row["latitude"]},{row["longitude"]}', axis = 1)
    fields = df.to_dict(orient = 'records')
    return render_template('fields.html', fields = fields)

@app.route('/sponsors', methods = ['GET'])
def sponsors():
    df = get_df('sponsors')
    sponsors = df.to_dict(orient = 'records')
    return render_template('sponsors.html', sponsors = sponsors)

@app.route('/', methods = ['GET'])
def home():
    return render_template('home.html', leagues = leagues(), events = events(), standings = standings())