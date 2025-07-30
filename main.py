from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Path, Query
from bs4 import BeautifulSoup
import requests

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
    return {'message': 'This API is for obtaining IESO demand, supply, and pricing data overall, and by zone.'}

@app.get('/demand/{year}') 
def get_demand(year: int = Path(le=current_year, ge=2003)):
    response = requests.get(DEMAND_URL_YEAR, timeout=5)
    soup = BeautifulSoup(response.text, 'html.parser')
    url = soup.find('a', href=f'PUB_Demand.csv')
    r = requests.get(f'{DEMAND_URL_YEAR}/{url.text}', stream=True)
    
    with open(f'PUB_Demand.csv', 'wb') as file:
        file.write(r.content)


    return {'message': f'For {current_year}, to see data for {current_month}/{current_day}, use demand/today or demand/now', 'number': year, 'url': url.text}

@app.get('/demand')
def get_demand_now():
    return {'message': f'Ontario Demand as of {current_hour}:{current_minute} is '}





