from arxiv_auth import domain
from datetime import datetime

n = 10

print("testing NamedTuple round trip")

for i in range(10):
    chunk = str(i)
    data = {'user_id':'1234' + chunk,
            'user_id':'12345',
            'email':f'foo{i}@bar.com',
            'username':f'emanresu{i}',
            'session_id': 1234 + i,
            'start_time':  datetime.now(),
            'name':{
                'forename':'First'+ chunk,
                'Last':'Last'+ chunk,
                'suffix':'Lastest'+chunk,
            },
            'profile':{
                'affiliation':'FSU',
                'rank':3,
                'country':'us',
                'default_category':'astro-ph.CO',
                'submission_groups':['grp_physics'],
                'homepage_url': 'http://example.com/' + chunk,
                'remember_me' : bool( i % 2)
            },
            'endorsements':['astro-ph.CO'],
            'authorizations':{
                'scopes':[
                    {
                        'action':'read',
                        'domain': 'submission',
                        'resource': None
                    },
                    {
                        'action': 'create',
                        'domain': 'submission',
                        'reosurce': None
                    }
                ],
            }
    }

    session = domain.from_dict(domain.Session, data)
    tripped = domain.to_dict(session)
    assert data == tripped
