#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import codecs
import os
from datetime import timedelta

from database import database
from alex.utils.config import online_update, to_project_path




# tab-separated file containing street + city + lon|lat coordinates + slot_specification
STREETS_LOCATIONS_FNAME = 'streets.locations.csv'
# tab-separated file containing stop + city + lon|lat coordinates
STOPS_LOCATIONS_FNAME = 'stops.locations.csv'
# tab-separated file containing city + state + lon|lat coordinates
CITIES_LOCATIONS_FNAME = 'cities.locations.csv'

# load new versions of the data files from the server
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), STREETS_LOCATIONS_FNAME)))
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), STOPS_LOCATIONS_FNAME)))
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), CITIES_LOCATIONS_FNAME)))

ontology = {
    'slots': {
        'silence': set([]),
        'ludait': set([]),
        'task': set(['find_connection', 'find_platform', 'weather']),
        'from_stop': set(['Central Park', 'Wall Street', ]),
        'to_stop': set(['Central Park', 'Wall Street', ]),
        'via_stop': set(['Central Park', 'Wall Street', ]),
        'from_street': set(['123 St', ]),
        'to_street': set(['100 Av', ]),
        'from_city': set([]),
        'to_city': set([]),
        'via_city': set([]),
        'in_city': set([]),
        'in_state': set([]),
        'departure_time': set([]),
        'departure_time_rel': set([]),
        'arrival_time': set([]),
        'arrival_time_rel': set([]),
        'time': set([]),
        'time_rel': set([]),
        'duration': set([]),
        'ampm': set(['morning', 'am', 'pm', 'evening', 'night']),
        'date': set([]),
        'date_rel': set(['today', 'tomorrow', 'day_after_tomorrow', ]),
        'centre_direction': set(['dontcare', 'dontknow', 'to', 'from', '*', ]),
        'num_transfers': set([]),
        'vehicle': set(["dontcare", "bus", "tram", "subway", "train", "cable_car", "ferry", "monorail"]),
        'alternative': set(['dontcare', '1', '2', '3', '4', 'last', 'next', 'prev', ]),
    },

    'slot_attributes': {
        'silence': [],
        'silence_time': [],
        'ludait': [],
        'task': [
            'user_informs',
            #'user_requests', 'user_confirms',
            #'system_informs', 'system_requests', 'system_confirms',
            #'system_iconfirms', 'system_selects',
        ],
        'from_stop': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
        'to_stop': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
         'from_street': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
        'to_street': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
        'via_stop': [
            'user_informs', 'user_requests', 'user_confirms',
            #'system_informs', 'system_requests',
            'system_confirms', 'system_iconfirms',
            #'system_selects',
        ],
        'from_city': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms',
        ],
        'to_city': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms',
        ],
        'via_city': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms',
        ],
        'in_city': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms',
        ],
        'in_state': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms',
        ],
        'departure_time': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'absolute_time',
        ],

        'departure_time_rel': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'relative_time',
        ],
        'arrival_time': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'absolute_time',
        ],
        'arrival_time_rel': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'relative_time',
        ],
        'time': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'absolute_time',
        ],
        'time_rel': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'relative_time',
        ],
        'duration': [
            'user_requests',
            'relative_time',
        ],
        'ampm': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms',
            'system_selects',
        ],
        # not implemented yet
        'date': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
        ],

        'date_rel': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
        ],
        'centre_direction': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
        'num_transfers': [
            'user_requests',
            'system_informs',
        ],
        'vehicle': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
        ],
        'alternative': [
            'user_informs',
            'system_informs',
            #'system_requests',
            'system_confirms',
            #'system_iconfirms',
            #'system_selects',
        ],
        'current_time': [
            'system_informs',
            'absolute_time',
        ],
        'route_alternative': [
            # this is necessary to be defined as it is a state variable used by the policy and automatically added to
            # the dialogue state
        ],
        'time_zone': [
            'system_informs',
            'absolute_time',
        ],

        'lta_task': [],
        'lta_time': [],
        'lta_date': [],
        'lta_departure_time': [],
        'lta_arrival_time': [],

        # not implemented yet
        'transfer_stops': [
            'user_requests',
        ],
        'temperature': [
            'temperature',
        ],
        'min_temperature': [
            'temperature_int',
        ],
        'max_temperature': [
            'temperature',
        ],
    },
    'reset_on_change': {
        # reset slots when any of the specified slots has changed, for matching changed slots a regexp is used
        'route_alternative': [
            '^from_stop$', '^to_stop$', '^via_stop$',
            '^departure_time$', '^departure_time_rel$',
            '^arrival_time$', '^arrival_time_rel$',
            '^to_city$', '^from_city$', '^via_city$',
        ],
#        'from_stop': ['^from_city$'],
#        'to_stop': ['^to_city$'],
#        'via_stop': ['^via_city$'],
    },
    'last_talked_about': {
        # introduces new slots as a marginalisation of different inputs
        # this is performed by converting dialogue acts into inform acts
        'lta_time': {
            # the following means, every time I talk about the time, it supports the value time in slot time_sel
            'time': [('^(inform|confirm|request|select)$', '^time$', ''), ],
            # the following means, every time I talk about the time_rel, it supports the value time_rel in slot time_sel
            'time_rel': [('', '^time_rel$', ''), ],
            # as a consequence, the last slot the user talked about will have the highest probability in the ``time_sel``
            # slot
            'date_rel': [('', '^date_rel$', '')],
        },
        'lta_date': {
            'date': [('', '^date$', ''), ],
            'date_rel': [('', '^date_rel$', ''), ],
        },
        'lta_departure_time': {
            'departure_time': [('', '^departure_time$', ''), ],
            'departure_time_rel': [('', '^departure_time_rel$', ''), ],
            'time': [('^(inform|confirm|request|select)$', '^time$', ''), ],
            'time_rel': [('', '^time_rel$', ''), ],
            'date_rel': [('', '^date_rel$', '')],
        },
        'lta_arrival_time': {
            'arrival_time': [('', '^arrival_time$', ''), ],
            'arrival_time_rel': [('', '^arrival_time_rel$', ''), ],
            'date_rel': [('', '^date_rel$', '')],
        },
        'lta_task': {
            'weather': [('', '^task$', '^weather$'), ],
            'find_connection': [('', '^task$', '^find_connection$'), ('', '^departure_', ''), ('', '^arrival_', ''),
                                ('', '^from_stop$', ''), ('', '^to_stop$', ''),
                                ('', '^duration$', '')],
        },
    },

    'compatibility': {
        'city_street':[
            'from_street', 'to_street',
        ],
        'stop_city': [
            'from_stop', 'to_stop', 'via_stop',
        ],
        'city_stop': [
            'from_city', 'to_city', 'via_city', 'in_city',
        ],
        'city_state': [
            'in_state',
        ],
    },
    'compatible_values': {
        'street_city': {},
        'city_street': {},
        'stop_city': {},
        'city_stop': {},
        'city_state': {},
        'state_city': {},
    },

    'default_values': {
        'in_city': 'New York',
        'in_state': 'New York',
        'time_zone_offset': timedelta(hours=-5),  # new york is 5 hours earlier than utc
    },

    'addinfo': {
        'city': {},
        'state': {},
        'stop_category' : {},
    },

    # translation of the values for TTS output
    'value_translation': {
        'ampm': {
            'morning': 'morning',
            'am': 'forenoon',
            'pm': 'afternoon',
            'evening': 'evening',
            'night': 'at night'
        },
        'vehicle': {
            'dontcare': 'any means',
            'bus': 'bus',
            'intercity_bus': 'coach',
            'night_bus': 'night bus',
            'monorail': 'monorail',
            'tram': 'tram',
            'night_tram': 'night tram',
            'subway': 'subway',
            'train': 'train',
            'cable_car': 'cable car',
            'ferry': 'ferry',
            'trolleybus': 'trolley',
            'substitute_traffic': 'alternative transport',
        },
        'date_rel': {
            'today': 'today',
            'tomorrow': 'tomorrow',
            'day_after_tomorrow': 'day after tomorrow'
        },
        'alternative': {
            'dontcare': 'arbitrary',
            '1': 'first',
            '2': 'second',
            '3': 'third',
            '4': 'fourth',
            'last': 'last',
            'next': 'next',
            'prev': 'previous',
        }
    },
}




def add_slot_values_from_database(slot, category, exceptions=set()):
    for value in database.get(category, tuple()):
        if value not in exceptions:
            ontology['slots'][slot].add(value)
add_slot_values_from_database('from_street', 'street')
add_slot_values_from_database('to_street', 'street')
add_slot_values_from_database('from_stop', 'stop')
add_slot_values_from_database('to_stop', 'stop')
add_slot_values_from_database('via_stop', 'stop')
add_slot_values_from_database('from_city', 'city')
add_slot_values_from_database('to_city', 'city')
add_slot_values_from_database('via_city', 'city')
add_slot_values_from_database('in_city', 'city')
add_slot_values_from_database('in_state', 'state')
add_slot_values_from_database('departure_time', 'time', exceptions=set(['now']))
add_slot_values_from_database('departure_time_rel', 'time')
add_slot_values_from_database('arrival_time', 'time', exceptions=set(['now']))
add_slot_values_from_database('arrival_time_rel', 'time')
add_slot_values_from_database('time', 'time', exceptions=set(['now']))
add_slot_values_from_database('time_rel', 'time')
add_slot_values_from_database('date_rel', 'date_rel')


def load_geo_values(fname, slot1, slot2, surpress_warning=True):
    with codecs.open(fname, 'r', 'UTF-8') as fh:
        for line in fh:
            if line.startswith('#'):
                continue
            value1, value2, geo = line.strip().split('\t')[0:3]
            value1 = value1.strip()
            value2 = value2.strip()
            geo = geo.strip()
            # expand geo coordinates
            lon, lat = geo.strip().split('|')
            if not value2 in ontology['addinfo'][slot2]:
                ontology['addinfo'][slot2][value2] = {}
            if value1 in ontology['addinfo'][slot2][value2] and not surpress_warning:
                print 'WARNING: ' + slot2 + " " + slot1 + " " + value1 + " already present!"
            ontology['addinfo'][slot2][value2][value1] = {'lon': lon, 'lat': lat}


def load_compatible_values(fname, slot1, slot2):
    with codecs.open(fname, 'r', 'UTF-8') as fh:
        for line in fh:
            if line.startswith('#'):
                continue
            val_slot1, val_slot2 = line.strip().split('\t')[0:2]
            # add to list of compatible values in both directions
            subset = ontology['compatible_values'][slot1 + '_' + slot2].get(val_slot1, set())
            ontology['compatible_values'][slot1 + '_' + slot2][val_slot1] = subset
            subset.add(val_slot2)
            subset = ontology['compatible_values'][slot2 + '_' + slot1].get(val_slot2, set())
            ontology['compatible_values'][slot2 + '_' + slot1][val_slot2] = subset
            subset.add(val_slot1)


def load_file_defined_slots(fname, surpress_warning=True):
    # we expect to see these slots in column 'slot':  'avenue', 'street', 'place'
    with codecs.open(fname, 'r', 'UTF-8') as fh:
        for line in fh:
            if line.startswith('#'):
                continue
            data = line.strip().split('\t')
            if len(data) < 4:
                print "ERROR: There is not enough fields to parse slot values in " + fname
                break
            value = data[0]
            slot = data[3].lower()
            prev_value = ontology['addinfo']['stop_category'].get(value, None)
            if prev_value and not surpress_warning:
                print 'WARNING: slot ' + value + " already contains " + prev_value + " (overwriting with " + slot + ")!"
            ontology['addinfo']['stop_category'][value] = slot


dirname = os.path.dirname(os.path.abspath(__file__))
load_file_defined_slots(os.path.join(dirname, STREETS_LOCATIONS_FNAME))

load_compatible_values(os.path.join(dirname, STREETS_LOCATIONS_FNAME), 'street', 'city')
load_compatible_values(os.path.join(dirname, STOPS_LOCATIONS_FNAME), 'stop', 'city')
load_compatible_values(os.path.join(dirname, CITIES_LOCATIONS_FNAME), 'city', 'state')

# load_geo_values(os.path.join(dirname, STREETS_LOCATIONS_FNAME), 'street', 'city')  # not supported - irrelevant, for places maybe, not for intersections tho
load_geo_values(os.path.join(dirname, STOPS_LOCATIONS_FNAME), 'stop', 'city')
load_geo_values(os.path.join(dirname, CITIES_LOCATIONS_FNAME), 'city', 'state')
