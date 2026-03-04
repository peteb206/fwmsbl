from config import db

def basic_query(collection: str):
    return list(db[collection].aggregate(pipeline = [
        {
            '$set': {
                '_id': {
                    '$toString': '$_id'
                }
            }
        }
    ]))

def leagues():
    return basic_query('leagues')

def fields():
    return basic_query('fields')

def sponsors():
    return basic_query('sponsors')

def teams():
    return list(db['teams'].aggregate(pipeline = [
        {
            '$lookup': {
                'from': 'leagues',
                'localField': 'league',
                'foreignField': '_id',
                'as': 'league'
            }
        }, {
            '$unwind': {
                'path': '$league',
                'preserveNullAndEmptyArrays': True
            }
        }, {
            '$set': {
                '_id': {
                    '$toString': '$_id'
                },
                'league._id': {
                    '$toString': '$league._id'
                }
            }
        }
    ]))

def practices():
    return list(db['practices'].aggregate(pipeline = [
        {
            '$lookup': {
                'from': 'teams',
                'localField': 'team',
                'foreignField': '_id',
                'as': 'team'
            }
        }, {
            '$unwind': {
                'path': '$team',
                'preserveNullAndEmptyArrays': True
            }
        }, {
            '$lookup': {
                'from': 'leagues',
                'localField': 'team.league',
                'foreignField': '_id',
                'as': 'league'
            }
        }, {
            '$unwind': {
                'path': '$league',
                'preserveNullAndEmptyArrays': True
            }
        }, {
            '$lookup': {
                'from': 'fields',
                'localField': 'field',
                'foreignField': '_id',
                'as': 'field'
            }
        }, {
            '$unwind': {
                'path': '$field',
                'preserveNullAndEmptyArrays': True
            }
        }, {
            '$set': {
                '_id': {
                    '$toString': '$_id'
                },
                'field._id': {
                    '$toString': '$field._id'
                },
                'league._id': {
                    '$toString': '$league._id'
                },
                'team._id': {
                    '$toString': '$team._id'
                },
                'team.league._id': {
                    '$toString': '$team.league._id'
                },
                'type': 'practice'
            }
        }
    ]))

def games():
    return list(db['games'].aggregate(pipeline = [
        {
            '$lookup': {
                'from': 'leagues',
                'localField': 'league',
                'foreignField': '_id',
                'as': 'league'
            }
        }, {
            '$unwind': {
                'path': '$league',
                'preserveNullAndEmptyArrays': True
            }
        }, {
            '$lookup': {
                'from': 'teams',
                'localField': 'team1',
                'foreignField': '_id',
                'as': 'team1'
            }
        }, {
            '$unwind': {
                'path': '$team1',
                'preserveNullAndEmptyArrays': True
            }
        }, {
            '$lookup': {
                'from': 'teams',
                'localField': 'team2',
                'foreignField': '_id',
                'as': 'team2'
            }
        }, {
            '$unwind': {
                'path': '$team2',
                'preserveNullAndEmptyArrays': True
            }
        }, {
            '$lookup': {
                'from': 'teams',
                'localField': 'home',
                'foreignField': '_id',
                'as': 'home'
            }
        }, {
            '$unwind': {
                'path': '$home',
                'preserveNullAndEmptyArrays': True
            }
        }, {
            '$lookup': {
                'from': 'fields',
                'localField': 'field',
                'foreignField': '_id',
                'as': 'field'
            }
        }, {
            '$unwind': {
                'path': '$field',
                'preserveNullAndEmptyArrays': True
            }
        }, {
            '$set': {
                '_id': {
                    '$toString': '$_id'
                },
                'league._id': {
                    '$toString': '$league._id'
                },
                'field._id': {
                    '$toString': '$field._id'
                },
                'team1._id': {
                    '$toString': '$team1._id'
                },
                'team1.league._id': {
                    '$toString': '$team1.league._id'
                },
                'team2._id': {
                    '$toString': '$team2._id'
                },
                'team2.league._id': {
                    '$toString': '$team2.league._id'
                },
                'home._id': {
                    '$toString': '$home._id'
                },
                'home.league._id': {
                    '$toString': '$home.league._id'
                },
                'type': 'game'
            }
        }
    ]))

if __name__ == '__main__':
    from pprint import pprint

    print('Leagues:')
    pprint(leagues())

    print('Fields:')
    pprint(fields())

    print('Sponsors:')
    pprint(sponsors())

    print('Teams')
    pprint(teams())

    print('Practices')
    pprint(practices())

    print('Games')
    pprint(games())
