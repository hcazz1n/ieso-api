from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Path, Query
from bs4 import BeautifulSoup
import requests
import pandas
import os
from lxml import etree
import xmltodict
import json
        

date = datetime.now(timezone(timedelta(hours=-4)))
current_year = date.year
current_month = ('0' + str(date.month), date.month)[date.month > 9]
current_day = ('0' + str(date.day), date.day)[date.day > 9]
current_hour = ('0' + str(date.hour), date.hour)[date.hour > 9]
current_minute = ('0' + str(date.minute), date.minute)[date.minute > 9]

DEMAND_URL_YEAR = 'https://reports-public.ieso.ca/public/Demand'
DEMAND_URL_NOW = 'https://reports-public.ieso.ca/public/RealtimeTotals'
SUPPLY_URL = ''
PRICE_URL = ''


def csv_to_json(response_csv, json_file_name, skip): #takes a csv retrieved from the IESO and converts it into a JSON file. skip is the number of rows to skip from the start of the file for data such as comments in the headers. Parses and returns EVERY column.
    with open('temp.csv', 'w') as file:
        file.write(response_csv.text)

    df = pandas.read_csv('temp.csv', skiprows=skip)
    json_file = open(f'./output/{json_file_name}.json', 'w+')
    df.to_json(json_file, orient='records', indent=4)
    json_file.close()
    #os.remove('./output/temp.csv')

    return json_file

app = FastAPI(title='IESO API')

@app.get('/')
def root():
    return 'This API is for obtaining IESO demand, supply, and pricing data overall, and by zone. /help to see all commands'

@app.get('/help')
def help():
    return {'/' : 'Navigates to the homepage.',
            '/help' : 'Navigates to the helper page', 
            '/demand' : f'Provides the current power demand in Ontario as of {current_hour}:{current_minute}', 
            '/demand/{year}' : f'Provides the current power demand in Ontario for any year between 2003 and {current_year}'}

@app.get('/demand/{year}') 
def get_demand(year: int = Path(le=current_year, ge=2003)):
    web_response = requests.get(DEMAND_URL_YEAR, timeout=5)
    soup = BeautifulSoup(web_response.text, 'html.parser')
    url = soup.find('a', href=f'PUB_Demand_{year}.csv')
    file_response = requests.get(f'{DEMAND_URL_YEAR}/{url.text}', stream=True)

    return csv_to_json(file_response, f'Demand_{year}', 3)


@app.get('/demand')
def get_demand_now():
    web_response = requests.get(DEMAND_URL_NOW, timeout=5)
    soup = BeautifulSoup(web_response.text, 'html.parser')
    url = soup.find('a', href=f'PUB_RealtimeTotals.xml')
    file_response = requests.get(f'{DEMAND_URL_NOW}/{url.text}', stream=True)

    with open('temp.xml', 'w') as file:
        file.write(file_response.text)
        
    tree = etree.parse('temp.xml', etree.XMLParser(remove_blank_text=True)) 
    #tree.write('temp.xml', pretty_print=True)

    for elem in tree.getiterator(): #remove namespaces from the tags to easily find desired data using xpath
        if isinstance(elem.tag, str) and elem.tag.startswith('{'):
            elem.tag = elem.tag.split('}', 1)[1] #takes the index after the split

    data = []
    interval_energy = tree.xpath('//IntervalEnergy')

    count = 0

    for i in interval_energy:
        interval = i.xpath('./Interval/text()')
        count += 1
        mq = i.xpath('./MQ')
        for j in mq:
            market_quantity = j.xpath('./MarketQuantity/text()')
            energy_mw = j.xpath('./EnergyMW/text()')

            data.append({
                'Interval': interval[0], #[0] is the first matching result, and there is only one MarketQuantity/EnergyMW in MQ and only one Interval in IntervalEnergy. Therefore, when iterating, to the next MQ/IntervalEnergy, [0] is always the next piece of data.
                market_quantity[0] : float(energy_mw[0]),
            })
    
    with open('./output/Demand_Now.json', 'w') as file:
        json.dump(data, file, indent=4)

    return_kv_market_demand = next(key for key in data if 'Total Energy' in key and key.get('Interval') == str(count))
    return_kv_ontario_demand = next(key for key in data if 'ONTARIO DEMAND' in key and key.get('Interval') == str(count))

    return {'message': f'As of {current_hour}:{current_minute} on {current_year}/{current_month}/{current_day}, Ontario Demand is {return_kv_ontario_demand['ONTARIO DEMAND']} MW, and Total Energy (Market Demand) is {return_kv_market_demand['Total Energy']} MW. Ontario Demand is {round((return_kv_ontario_demand['ONTARIO DEMAND']/float(return_kv_market_demand['Total Energy']))*100, 2)}% of the Total Energy supplied by the IESO.'}





