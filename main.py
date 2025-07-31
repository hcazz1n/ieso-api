from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Path, Query
from bs4 import BeautifulSoup
import requests
import pandas
import os

class Demand:
    def __init__(self, date, hour, ont_demand, total_energy):
        self.date = date
        self.hour = hour
        self.ont_demand = ont_demand
        self.total_energy = total_energy #AKA Market Demand
        

date = datetime.now(timezone(timedelta(hours=-4)))
current_year = date.year
current_month = date.month
current_day = date.day
current_hour = date.hour
current_minute = date.minute

DEMAND_URL_YEAR = 'https://reports-public.ieso.ca/public/Demand'
DEMAND_URL_NOW = 'https://reports-public.ieso.ca/public/RealtimeTotals'
SUPPLY_URL = ''
PRICE_URL = ''

app = FastAPI(title='IESO API')

@app.get('/')
def root():
    return 'This API is for obtaining IESO demand, supply, and pricing data overall, and by zone. /help to see all commands'

@app.get('/help')
def help():
    return {'/' : 'Takes you to the homepage.', 
            '/demand' : f'Provides the current power demand in Ontario as of {current_hour}:{current_minute}', 
            '/demand/{year}' : f'Provides the current power demand in Ontario for any year between 2003 and {current_year}'}

@app.get('/demand/{year}') 
def get_demand(year: int = Path(le=current_year, ge=2003)):
    web_response = requests.get(DEMAND_URL_YEAR, timeout=5)
    soup = BeautifulSoup(web_response.text, 'html.parser')
    url = soup.find('a', href=f'PUB_Demand_{year}.csv')
    file_response = requests.get(f'{DEMAND_URL_YEAR}/{url.text}', stream=True)

    with open(f'./output/PUB_Demand.csv', 'wb') as file:
        file.write(file_response.content)
    
    df = pandas.read_csv('./output/PUB_Demand.csv', skiprows=3)
    json_file = open(f'./output/Demand_{year}.json', 'w+')
    df.to_json(json_file, orient='records', indent=4)
    json_file.close()
    os.remove('./output/PUB_Demand.csv')

    return json_file

@app.get('/demand')
def get_demand_now():
    return {'message': f'Ontario Demand as of {current_hour}:{current_minute} is '}





