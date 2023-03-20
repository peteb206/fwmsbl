import pandas as pd
from datetime import datetime, timedelta
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, jsonify, request, render_template, redirect
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASSWORD')
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

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
    google_sheet = client.open_by_key('1TABdL_mWjF4RCfdDbqXYflaJzjOhveM5RdtyrkpHdGQ')
    worksheet_dict = {
        'leagues': google_sheet.get_worksheet_by_id(1586626557),
        'teams': google_sheet.get_worksheet_by_id(931255258),
        'games': google_sheet.get_worksheet_by_id(1416711061),
        'fields': google_sheet.get_worksheet_by_id(1923145408)
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
        return f'{game_data["team1"]} vs. {game_data["team2"]}'
    elif int(game_data['team2_score']) > int(game_data['team1_score']):
        return f'{game_data["team2"]} beat {game_data["team1"]} {game_data["team2_score"]}-{game_data["team1_score"]}'
    elif int(game_data['team2_score']) < int(game_data['team1_score']):
        return f'{game_data["team1"]} beat {game_data["team2"]} {game_data["team1_score"]}-{game_data["team2_score"]}'
    else:
        return f'{game_data["team1"]} tied {game_data["team2"]} {game_data["team1_score"]}-{game_data["team2_score"]}'

# API
@app.route('/api/events', methods = ['GET'])
def events_api():
    league = request.args.get('league', type = str)
    team = request.args.get('team', type = str)
    start = request.args.get('start', type = str)
    end = request.args.get('end', type = str)

    games_df = get_df('games')
    df_filter = pd.Series([True for _ in range(len(games_df.index))])
    if league not in ['', None]:
        # Filter by league
        df_filter = games_df['league'] == league
    if team not in ['', None]:
        # Filter by team
        df_filter = df_filter & ((games_df['team1'] == team) | (games_df['team2'] == team))
    df = games_df[df_filter].copy()

    # Handle dates
    df['start'] = pd.to_datetime(df['start'])
    df['end'] = df['start'].apply(lambda start: start + timedelta(hours = 3)) # Games last 3 hours
    if (start not in ['', None]) & (end not in ['', None]):
        # Filter by date
        df_filter = df_filter & (df['start'] >= datetime.strptime(f'{start}Z', full_calendar_date_format)) & (df['end'] <= datetime.strptime(f'{end}Z', full_calendar_date_format))
    df['start'] = df['start'].dt.strftime(full_calendar_date_format)
    df['end'] = df['end'].dt.strftime(full_calendar_date_format)

    # Get supplemental data
    df['field'] = df['field'].str.replace(r'^$', 'Location TBD', regex = True)
    df = df.merge(get_df('leagues').rename({'name': 'league'}, axis = 1), how = 'left', on = 'league')
    df['title'] = df.apply(lambda row: f'{row["league"] + " - " if league in ["", None] else ""}{format_game_result(row)} ({row["field"]})', axis = 1) if len(df.index) > 0 else ''
    return jsonify(df.to_dict(orient = 'records'))

@app.route('/api/leagues', methods = ['GET'])
def leagues_api():
    return jsonify(get_df('leagues').to_dict(orient = 'records'))

@app.route('/api/fields', methods = ['GET'])
def fields_api():
    df = get_df('fields')
    df['link'] = df.apply(lambda row: f'https://www.google.com/maps/place/{row["latitude"]},{row["longitude"]}', axis = 1)
    return jsonify(df.to_dict(orient = 'records'))

@app.route('/api/teams', methods = ['GET'])
def teams_api():
    league = request.args.get('league', type = str)
    name = request.args.get('name', type = str)

    teams_df = get_df('teams')
    df_filter = pd.Series([True for _ in range(len(teams_df.index))])
    if league not in ['', None]:
        # Filter by league
        df_filter = df_filter & (teams_df['league'] == league)
    if name not in ['', None]:
        # Filter by name
        df_filter = df_filter & (teams_df['name'] == name)
    df = teams_df[df_filter].copy()
    return jsonify(df.to_dict(orient = 'records'))

@app.route('/api/standings', methods = ['GET'])
def standings_api():
    league = request.args.get('league', type = str)

    games_df, teams_df = get_df('games'), get_df('teams')
    df_filter = (games_df['team1_score'] != '') & (games_df['team2_score'] != '')
    if league not in ['', None]:
        # Filter by league
        df_filter = df_filter & (games_df['league'] == league)
        teams_df = teams_df[teams_df['league'] == league]
    df, standings_df, wlt = games_df[df_filter].copy(), None, ['W', 'L', 'T']
    if len(df.index) == 0:
        standings_df = teams_df.drop('league', axis = 1)
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

        standings_df = teams_df.merge(results_df.reset_index(), how = 'left', on = 'name').drop('league', axis = 1).sort_values(by = 'winPct', ascending = False)
    return jsonify(standings_df.fillna(0).astype({'W': int, 'L': int, 'T': int}).to_dict(orient = 'records'))

# Email
@app.route('/contact', methods = ['POST'])
def contact():
    regarding = request.form.get('regarding', '')
    name = request.form.get('name', '')
    phone = request.form.get('phone', '')
    email = request.form.get('email', '')
    message = request.form.get('message', '')
    send_test = request.form.get('address', '')

    if send_test == '':
        msg = Message("Fort Worth Men's Senior Baseball League: Contact Us", sender = f'FWMSBL Website <{os.environ.get("EMAIL_USERNAME")}>', recipients = [os.environ.get('EMAIL_RECIPIENT')])
        msg.html = f'''
            <h2>Contact Us Submission</h2>
            <b>Regarding:</b> {regarding}<br>
            <b>Name:</b> {name}<br>
            <b>Phone:</b> {phone}<br>
            <b>Email:</b> {email}<br>
            <b>Message:</b> {message}<br>
        '''
        mail.send(msg)
    return redirect('/')

@app.route('/freeAgent', methods = ['POST'])
def free_agent():
    name = request.form.get('name', '')
    age = request.form.get('age', '')
    phone = request.form.get('phone', '')
    email = request.form.get('email', '')
    send_test = request.form.get('address', '')

    if send_test == '':
        msg = Message("Fort Worth Men's Senior Baseball League: Free Agent", sender = f'FWMSBL Website <{os.environ.get("EMAIL_USERNAME")}>', recipients = [os.environ.get('EMAIL_RECIPIENT')])
        msg.html = f'''
            <h2>Free Agent Submission</h2>
            <b>Name:</b> {name}<br>
            <b>Age:</b> {age}<br>
            <b>Phone:</b> {phone}<br>
            <b>Email:</b> {email}<br>
        '''
        mail.send(msg)
    return redirect('/')

@app.route('/waiver', methods = ['POST'])
def submit_waiver():
    name = request.form.get('name', '')
    first_name = request.form.get('firstName', '')
    last_name = request.form.get('lastName', '')
    local_league = request.form.get('localLeague', '')
    dob = request.form.get('dob', '')
    phone = request.form.get('phone', '')
    email = request.form.get('email', '')
    no_pro = request.form.get('noProfessional', '')
    last_pro_year = request.form.get('professionalLastYear', '')
    highest_level_played = request.form.get('professionalHighestLevel', '')
    send_test = request.form.get('address', '')

    if send_test == '':
        msg = Message(f"Fort Worth Men's Senior Baseball League: {name} Player Waiver", sender = f'FWMSBL Website <{os.environ.get("EMAIL_USERNAME")}>', recipients = [os.environ.get('EMAIL_RECIPIENT')])
        msg.html = f'''
            <h2>Player Waiver Submission</h2>
            <b>Name:</b> {name}<br>
            <b>First Name:</b> {first_name}<br>
            <b>Last Name:</b> {last_name}<br>
            <b>Local MSBL/MABL League Playing In:</b> {local_league}<br>
            <b>Date of Birth:</b> {dob}<br>
            <b>Phone:</b> {phone}<br>
            <b>Email:</b> {email}<br>
            <b>I have never played any level of professional baseball:</b> {no_pro == "on"}<br>
            <b>I have played professional baseball, last year played:</b> {last_pro_year}<br>
            <b>I have played professional baseball, highest level played:</b> {highest_level_played}<br>
        '''
        mail.send(msg)
    return redirect('/waiver')

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