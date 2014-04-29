#!/usr/bin/env python3

# all stdlib imports
import argparse
import json
import operator
import os
import sys
import tempfile
import zipfile
from urllib import request

# The base url for requesting from the netrunnerdb api
APIBASE = 'http://netrunnerdb.com/api'

# AFAICT this is not programmatically available from netrunnerdb...if it were,
# we should prefer that
CYCLE_MAP = {
    'Genesis': {'wla', 'ta', 'ce', 'asis', 'hs', 'fp'},
    'Spin': {'om', 'st', 'mt', 'tc', 'fal', 'dt'},
    'Lunar': {'up', 'tsb', 'fc'},
}

# These are cases where the netrunnerdb.com name for a set differs from the
# OCTGN A:NR plugin name for the same set
SPECIAL_CASE_OVERRIDES = {
    'Special': 'Promos',
    'special': 'Promos',
}

def build_parser(dp_choices):
    """Return a cli parser. Takes a list of data pack name choices as input."""
    parser = argparse.ArgumentParser('Build octgn A:NR spoiler sets')
    parser.add_argument('-n', '--data-pack-name', choices=dp_choices,
        required=True,
        help='Name of the data pack to contruct spoiler for')
    parser.add_argument('-d', '--octgn-dir', type=str, default='OCTGN',
        help='OCTGN base path')
    parser.add_argument('-g', '--game-id', type=str,
        default='0f38e453-26df-4c04-9d67-6d43de939c77',
        help='OCTGN game id for A:NR')
    parser.add_argument('-p', '--card-id-prefix', type=str,
        default='bc0f047c-01b1-427f-a439-d451eda',
        help='prefix for card image file')
    parser.add_argument('-o', '--output-dir', default='.', type=str,
        help='Directory to place output file')
    return parser

def get_json(url):
    """Wrapper for retrieving and parsing json data from a url"""
    response = request.urlopen(url)
    # .decode() has to be called because urlopen returns bytes, and json.load()
    # expects str
    return json.loads(response.read().decode())

def get_cards_for_set(set_data, game_id, octgn_dir, card_id_prefix, zfile):
    """adds images for a set to the zip file"""
    set_id = get_set_id(set_data['name'], octgn_dir, game_id)
    set_path = os.path.join(game_id, 'Sets', set_id, 'Cards')
    card_data = get_json('{}/set/{}'.format(APIBASE, set_data['code']))
    for card in card_data:
        img = request.urlopen('http://netrunnerdb.com' + card['largeimagesrc'])
        card_path = os.path.join(set_path, '{}{}.png'.format(card_id_prefix,
                                                             card['code']))
        zfile.writestr(card_path, img.read())

def get_set_id(name, octgn_dir, game_id):
    """Parses the octgn plugin xml files to figure out the id for a set"""
    if name in SPECIAL_CASE_OVERRIDES:
        name = SPECIAL_CASE_OVERRIDES[name]
    set_base=os.path.join(os.path.abspath(octgn_dir),
        'GameDatabase', game_id, 'Sets')
    for set_id in os.listdir(set_base):
        xml_path = os.path.join(set_base, set_id, 'set.xml')
        with open(xml_path, 'r') as fh:
            for line in fh.readlines():
                line = line.lower()
                if '  name=' in line:
                    if name.lower().replace(' set', '') in \
                        line.replace('&amp;', 'and'):
                        return set_id

def main():
    """The main program. Parse the cli, figure out which data packs to download,
    and what to name the output file, get the images and write the zip"""
    # Get from the site the list of data packs that exist. Takes full names as
    # well as short codes
    data_packs = get_json('{}/sets/'.format(APIBASE))
    dp_choices = set(map(operator.itemgetter('name'), data_packs))
    dp_choices.update(map(operator.itemgetter('code'), data_packs))
    dp_choices.update(CYCLE_MAP.keys())
    parser = build_parser(dp_choices)
    args = parser.parse_args()
    print('opening temp file to write zip')
    # We don't know what the file will be named yet
    temp_file = tempfile.mktemp()
    zfile = zipfile.ZipFile(temp_file, 'w')
    # Figure out which packs to get
    if args.data_pack_name in CYCLE_MAP:
        sets_to_get = CYCLE_MAP[args.data_pack_name]
        output_name = 'Cycle ' + args.data_pack_name
    else:
        sets_to_get = [args.data_pack_name]
        output_name = None
    # If somebody spends more than 60 seconds thinking about it there's probably
    # a better way, but this gets the job done
    for name in sets_to_get:
        for pack in data_packs:
            if name in (pack['name'], pack['code']):
                print('Getting cards for {}'.format(pack['name']))
                # Add the cards to the zip
                get_cards_for_set(pack, args.game_id, args.octgn_dir,
                                  args.card_id_prefix, zfile)
                if output_name is None:
                    output_name = pack['name']
    print('Closing zip file')
    zfile.close()
    out_path = os.path.join(args.output_dir,
                            'ANR-{}.o8c'.format(output_name.replace(' ', '-')))
    print('Moving temp zip file to {}'.format(out_path))
    os.rename(temp_file, out_path)

if __name__ == "__main__":
    main()
