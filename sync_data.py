from config import db, google_sheet
from datetime import datetime, timedelta

def get_google_sheets_records(sheet_name: str) -> list[dict]:
    google_worksheet = google_sheet.worksheet(sheet_name)
    google_sheets_records = list()
    for record in google_worksheet.get_all_records():
        record = {k: v for k, v in record.items() if v != ''}
        if record != dict():
            google_sheets_records.append(record)
    return google_sheets_records

def replace_with_google_sheets_records(collection: str):
    print(collection)
    google_sheets_records = get_google_sheets_records(sheet_name = collection.title())
    db[collection].drop()
    db[collection].insert_many(google_sheets_records)

def map_labels_to_ids(list_with_labels: list, label_key: str, list_with_ids: list, label_key2: str):
    output_list = list()
    for dict_with_label in list_with_labels:
        dicts_with_id = list(filter(lambda d: d[label_key2] == dict_with_label[label_key] if label_key in dict_with_label.keys() else False, list_with_ids))
        if len(dicts_with_id) == 0:
            if label_key in dict_with_label.keys():
                del dict_with_label[label_key]
        else:
            dict_with_id = dicts_with_id[0]
            dict_with_label[label_key] = dict_with_id['_id']
        output_list.append(dict_with_label)
    return output_list

def set_start_and_end(records):
    output_records = list()
    for record in records:
        if 'date' not in record.keys(): continue
        record['start'] = datetime.strptime(f'{record["date"]} {record["start"]}', '%m/%d/%Y %I:%M %p')
        if 'league' in record.keys():
            record['end'] = record['start'] + timedelta(hours = 3)  # Games last 3 hours
        else:
            record['end'] = datetime.strptime(f'{record["date"]} {record["end"]}', '%m/%d/%Y %I:%M %p')
        del record['date']
        output_records.append(record)
    return output_records

def sync_google_sheet_and_mongo_db():
    # Easy ones
    replace_with_google_sheets_records('leagues')
    replace_with_google_sheets_records('fields')
    replace_with_google_sheets_records('sponsors')

    # Teams
    print('teams')
    google_sheet_teams = get_google_sheets_records(sheet_name = 'Teams')
    db_leagues = list(db['leagues'].find())
    db_teams_upload = map_labels_to_ids(google_sheet_teams, 'league', db_leagues, 'name')
    db['teams'].drop()
    db['teams'].insert_many(db_teams_upload)

    # Practices
    print('practices')
    google_sheet_practices = get_google_sheets_records(sheet_name = 'Practices')
    db_teams = list(db['teams'].find())
    db_fields = list(db['fields'].find())
    dp_practices_upload = map_labels_to_ids(google_sheet_practices, 'team', db_teams, 'name')
    dp_practices_upload = map_labels_to_ids(dp_practices_upload, 'field', db_fields, 'name')
    dp_practices_upload = set_start_and_end(dp_practices_upload)
    db['practices'].drop()
    db['practices'].insert_many(dp_practices_upload)

    # Games
    print('games')
    google_sheet_games = get_google_sheets_records(sheet_name = 'Games')
    db_leagues = list(db['leagues'].find())
    db_teams = list(db['teams'].find())
    db_fields = list(db['fields'].find())
    dp_games_upload = map_labels_to_ids(google_sheet_games, 'league', db_leagues, 'name')
    dp_games_upload = map_labels_to_ids(dp_games_upload, 'team1', db_teams, 'name')
    dp_games_upload = map_labels_to_ids(dp_games_upload, 'team2', db_teams, 'name')
    dp_games_upload = map_labels_to_ids(dp_games_upload, 'home', db_teams, 'name')
    dp_games_upload = map_labels_to_ids(dp_games_upload, 'field', db_fields, 'name')
    dp_games_upload = set_start_and_end(dp_games_upload)
    db['games'].drop()
    db['games'].insert_many(dp_games_upload)

    db['google_sheet_last_update'].drop()
    db['google_sheet_last_update'].insert_one({'timestamp': google_sheet.lastUpdateTime})

if __name__ == '__main__':
    google_sheet_last_update = db['google_sheet_last_update'].find_one()['timestamp']
    if google_sheet_last_update == google_sheet.lastUpdateTime:
        print(f'No Google Sheet updates since the last one at {google_sheet_last_update}')
    else:
        sync_google_sheet_and_mongo_db()
