import argparse
import configparser
import os
from pathlib import Path
from tesselation_generator import rect_tess_maker
import GCN_utils as gcn
from lvc_handler import generate_fields_from_skymap, save_targets_to_file
from Fermi_handler import Fermi_handle
from scheduler_utilities import filter_for_visibility
from config_utils import make_config_file
import numpy as np
from paths import FLEMOS_DIR, CONFIGS_DIR, TESS_DIR, SKYMAPS_DIR, TESTS_DIR
import sys



def main():
    parser = argparse.ArgumentParser(description="change this NOW")
    parser.add_argument('-t', dest='t', type=str)
    parser.add_argument('-voe', dest='voe', type=str)
    parser.add_argument('-e', dest='e', type=str)
    parser.add_argument('-area', dest='area', type=str)
    parser.add_argument('-o', dest='o', type=str)

    args = parser.parse_args()
    outpath = args.o
    telescope = args.t
    eventfile = args.voe
    eventid = args.e

    
    if telescope == None:
        telescope = input('please enter telescope name: ')
        # telescope = 'RASA11'
    
    if not eventfile and not eventid:
        entry = input('please provide event name or VOEvent.xml file: ')
        if entry[-4:] == '.xml':
            eventfile = entry
        else:
            LVCevent = entry

        #FERMI test
        # eventfile = f'{TESTS_DIR}/gcn.classic.voevent.FERMI_GBM_POS_TEST_4586.xml'

        #LVC test
        # eventfile = f'{TESTS_DIR}/gcn.classic.voevent.LVC_INITIAL_7496.xml'


    
    if eventfile:
        if eventid:
                print('it is unnecessary to provide both event and event file, either will do')
        if gcn.get_ivorn(eventfile) == 'Fermi':
            if eventid:
                print('if you are going to give both an event and event file, make sure theyre for the same type of notice')
                exit()
            fermi = True
            lvc = False
        elif gcn.get_ivorn(eventfile) == 'LVC':
            if eventid and not eventid == gcn.getEvent(eventfile):
                print('if you are going to give both an event and event file, make sure theyre for the same event')
                exit()
            eventid = gcn.getEvent(eventfile)
            lvc = True
            fermi = False
        else:
            print('Notice type not supported')
            exit()      
    else:
        lvc = True
        fermi=False

    config = configparser.ConfigParser()
    default = configparser.ConfigParser()
    default.read(f'data/configs/default.cfg')

    if os.path.exists(f'{CONFIGS_DIR}/{telescope}.cfg'):
        config.read(f'{CONFIGS_DIR}/{telescope}.cfg')
    else:
        make_config_file(telescope, CONFIGS_DIR)

    try:
        lat = float(config[telescope]['lat'])
        lon = float(config[telescope]['lon'])
        RAfov = float(config[telescope]['RAfov'])
        DECfov = float(config[telescope]['DECfov'])
        elevation = float(config[telescope]['elevation'])
    except:
        print('flemopt config files MUST contain the following items: lat, lon, RAfov, DECfov and elevation. Default settings will be used for parameters not provided in configuration file')
    
    try:
        tileScale = float(config[telescope]['tileScale'])
    except:
        tileScale = float(default['telescope']['tileScale'])

    try:
        minObsChance = float(config[telescope]['minObsChance'])
    except:
        minObsChance = float(default['telescope']['minObsChance'])

    try:
        horizon = float(config[telescope]['horizon'])
    except:
        horizon = float(default['telescope']['horizon'])


    if not os.path.exists(f'{TESS_DIR}/{telescope}.tess'):
        rect_tess_maker(telescope, RAfov, DECfov, tileScale)
    if not outpath:
        try:
            outpath = config[telescope]['default_output_path']
        except:
            outpath = default['telescope']['default_output_path']
    
    if not os.path.exists(outpath):
        os.mkdir(outpath)

    if lvc:
        skymap_path =gcn.get_skymap(eventid, SKYMAPS_DIR)
        sorted_fields, ids_to_fields = generate_fields_from_skymap(skymap_path, RAfov, DECfov, tileScale, minObsChance)
        targets = [(id, np.rad2deg(ids_to_fields[id][0]), np.rad2deg(ids_to_fields[id][1])) for id, _ in sorted_fields]
        if args.area:
            gcn.area(minObsChance, skymap_path)
        # print(targets)
        # print(ids_to_fields)
    
    if fermi:
        targets, error = Fermi_handle(telescope, eventfile, RAfov, DECfov)
        # print(targets)
        if args.area:
            print(f'Search area is: {np.pi*(error^2)} square degrees')

    filtered_targets = filter_for_visibility(targets, lat, lon, elevation, 'nautical', telescope, horizon)
    # print(filtered_targets)
    save_targets_to_file(filtered_targets, f'{outpath}/{telescope}_targets.txt')

    


if __name__ == '__main__':
    main()