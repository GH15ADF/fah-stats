#!/usr/bin/python3
"""Get and store your Folding at Home stats

This script uses the [Folding At Home API](https://stats.foldingathome.org/api) to
retrieve the current statistics for a given user. Additionally, it allows saving the
returned statistics into a CSV file or InfluxDB database for historical analysis.
"""

import requests
import csv
import json
import logging
import time
import sys
import os
from datetime import datetime
from influxdb import InfluxDBClient

# append the path to the main script to the system path so other modules 
# can get pulled in when executing via cron
sys.path.append(os.path.split(os.path.realpath(__file__))[0])

# Some critical but individual settings are in the config_settings.py file
try:
    from config_settings import configs
except ImportError:
    print('Individual settings are kept in configs_settings.py, please add them there!')
    raise

start_time = time.time()

# call this first to configure the logger
logging.basicConfig(level=logging.DEBUG, filename=configs['user_stats_log'],
                    format='%(asctime)s - %(levelname)s-%(message)s')

# sometimes the API returns an error
try:
    res = requests.get('https://statsclassic.foldingathome.org/api/donor/' + configs['fah_user'])
except Exception as e:
    logging.exception("Exception occurred")

res.raise_for_status()
stats = res.json()

# extract information from response
wu = stats["wus"]
rank = stats["rank"]
total_users = stats["total_users"]
credit = stats["credit"]

# prepare InfluxDB record
output_dict = {}
output_dict["measurement"] = configs['historic_measure']
output_dict["time"] = datetime.today().strftime('%FT11:00:00Z')
field_dict = {}
field_dict["Rank"] = rank
field_dict["Out Of"] = total_users
field_dict["Score"] = credit
field_dict["WU"] = wu
output_dict["fields"] = field_dict
out_list = []
out_list.append(output_dict)
logging.info('InfluxDB record: {}'.format(out_list))

# write to CSV
if configs['write_history_to_csv']:
    with open(configs['csv_file'], 'a', newline='') as csvfile:
        fieldnames = ['Date', 'Rank', 'Out Of', "Score", 'WU']
        outfile  = csv.DictWriter(csvfile, fieldnames=fieldnames)
        outfile.writerow({"Date" : datetime.today().strftime('%m/%d/%Y'), 'Rank' : rank, 'Out Of' : total_users, "Score" : credit, 'WU' : wu})

# write to influx DB
if configs['write_history_to_influx']:
    try:
        client = InfluxDBClient(host=configs['influx_host'], port=8086)
        client.switch_database(configs['influx_db'])
        client.write_points(out_list)
    except Exception as e:
        logging.exception("Exception occurred")

elapsed_time = time.time() - start_time

logging.info('Done: {:.2f} seconds'.format(elapsed_time))

