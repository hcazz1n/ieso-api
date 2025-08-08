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
current_month = date.month
current_day = date.day
current_hour = date.hour
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
    tree.write('temp.xml', pretty_print=True) #delete after

    for elem in tree.getiterator(): #remove namespaces from the tags to easily find desired data using xpath
        if isinstance(elem.tag, str) and elem.tag.startswith('{'):
            elem.tag = elem.tag.split('}', 1)[1]

    data = []
    mq_elements = tree.xpath('//MQ')

    for tag in mq_elements:
        market_quantity = tag.xpath('./MarketQuantity/text()')
        energy_mw = tag.xpath('./EnergyMW/text()')

        data.append({
            'MarketQuantity': market_quantity[0] if market_quantity else None,
            'EnergyMW': float(energy_mw[0]) if energy_mw else None
        })
    
    with open('./output/Demand_Now.json', 'w') as file:
        json.dump(data, file, indent=4)

    values1 = tree.xpath('//MarketQuantity/text()')
    values2 = tree.xpath('//EnergyMW/text()')
    print(values1)
    print(values2)

    # count = 0
    # while(market_quantity):
    #     count += 1

    return {'message': f'Ontario Demand as of {current_hour}:{current_minute} on {current_year}{current_month}{current_day} is '}





