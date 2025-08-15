from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Path, Query
from bs4 import BeautifulSoup
import requests
import pandas
import os
from lxml import etree
import json
        

date = datetime.now(timezone(timedelta(hours=-4)))
current_year = date.year
current_month = ('0' + str(date.month), date.month)[date.month > 9]
current_day = ('0' + str(date.day), date.day)[date.day > 9]
current_hour = ('0' + str(date.hour), date.hour)[date.hour > 9]
current_minute = ('0' + str(date.minute), date.minute)[date.minute > 9]

DEMAND_URL_YEAR = 'https://reports-public.ieso.ca/public/Demand'
DEMAND_URL_NOW = 'https://reports-public.ieso.ca/public/RealtimeTotals'
SUPPLY_URL = 'https://reports-public.ieso.ca/public/GenOutputCapability'
PRICE_URL_ZONAL = 'https://reports-public.ieso.ca/public/RealtimeZonalEnergyPrices/'


def get_link(web_link, doc_link): #gets the link to the xml/csv doc and downloads it for parsing
    web_response = requests.get(web_link)
    soup = BeautifulSoup(web_response.text, 'html.parser')
    url = soup.find('a', href=doc_link)
    file_response = requests.get(f'{web_link}/{url.text}', stream=True)
    return file_response

def parse_xml(file_response): #parses downloaded XML and returns the ElementTree
    with open('temp.xml', 'w') as file:
        file.write(file_response.text)
        
    tree = etree.parse('temp.xml', etree.XMLParser(remove_blank_text=True))  #returns an element tree object (XML doc as a tree structure)
    tree.write('temp.xml', pretty_print=True) #rewrites the temp.xml doc for easier navigation

    for elem in tree.getiterator(): #remove namespaces from the tags to easily find desired data using xpath
        if isinstance(elem.tag, str) and elem.tag.startswith('{'):
            elem.tag = elem.tag.split('}', 1)[1] #takes the index after the split
    
    #os.remove('./temp.xml')
    return tree

def csv_to_json(response_csv, json_file_name, skip): #takes a csv retrieved from the IESO and converts it into a JSON file. skip is the number of rows to skip from the start of the file for data such as comments in the headers. Parses and returns EVERY column.
    with open('temp.csv', 'w') as file:
        file.write(response_csv.text)

    df = pandas.read_csv('temp.csv', skiprows=skip)
    json_file = open(f'./output/{json_file_name}.json', 'w+')
    df.to_json(json_file, orient='records', indent=4)
    json_file.close()
    #os.remove('./temp.csv')
    return json_file

def delete_none(d): #deletes all null/None values from a dict d
    for key, value in list(d.items()):
        if value is None:
            del d[key]
        elif isinstance(value, dict): #if value is a dict (i.e., sub-dictionaries) recursively call delete_none for the sub-dicts
            delete_none(value)
            if value == {}: #deletes any empty keys caused by deleting a sub-dictionary with content in it
                del d[key]

app = FastAPI(title='IESO API')

@app.get('/')
def root():
    return 'This API is for obtaining IESO demand, supply, and pricing data overall, and by zone. /help to see all commands'

@app.get('/help')
def help():
    return {'/': 'Navigates to the homepage.',
            '/help': 'Navigates to the helper page', 
            '/demand': f'Provides the current power demand in Ontario as of {current_hour}:{current_minute}', 
            '/demand/{year}': f'Provides the current power demand in Ontario for any year between 2003 and {current_year}'}


@app.get('/demand')
@app.get('/demand/now')
def get_demand_now():
    file_response = get_link(DEMAND_URL_NOW, 'PUB_RealtimeTotals.xml')
    tree = parse_xml(file_response)

    data = []
    interval_energy = tree.xpath('//IntervalEnergy')

    count = 0

    for i in interval_energy:
        mq_data = {}
        interval = i.xpath('./Interval/text()')
        count += 1
        mq = i.xpath('./MQ')
        for j in mq:
            market_quantity = j.xpath('./MarketQuantity/text()')
            energy_mw = j.xpath('./EnergyMW/text()')
            mq_data[market_quantity[0]] = float(energy_mw[0])

        data.append({
            int(interval[0]): mq_data #[0] is the first matching result, and there is only one MarketQuantity/EnergyMW in MQ and only one Interval in IntervalEnergy. Therefore, when iterating, to the next MQ/IntervalEnergy, [0] is always the next piece of data.
        })
    
    with open('./output/demand_realtime.json', 'w') as file:
        json.dump(data, file, indent=4)

    return_market_demand = next(dict[count]['Total Energy'] for dict in data if count in dict)
    return_ontario_demand = next(dict[count]['ONTARIO DEMAND'] for dict in data if count in dict)

    return {f'Returned JSON with five-minute intervals for {current_hour}:00. As of {current_hour}:{current_minute} on {current_year}/{current_month}/{current_day}, Ontario Demand is {return_ontario_demand} MW, and Total Energy (Market Demand) is {return_market_demand} MW. Ontario Demand is {round((return_ontario_demand/float(return_market_demand))*100, 2)}% of the Total Energy supplied by the IESO.'}

@app.get('/demand/{year}') 
def get_demand(year: int = Path(le=current_year, ge=2003)):
    file_response = get_link(DEMAND_URL_YEAR, f'PUB_Demand_{year}.csv')
    csv_to_json(file_response, f'demand_{year}', 3)

    return f'Demand for {year} successfully found.'

@app.get('/supply')
def get_supply():
    file_response = get_link(SUPPLY_URL, 'PUB_GenOutputCapability.xml')
    tree = parse_xml(file_response)

    data = []
    generators = tree.xpath('//Generator') #gets all the generator tags (not generators tag since there is only 1)

    gen_count = 0

    for generator in generators: #iterates through each generator found using xpath
        output_data = {}
        capability_data = {}
        capacity_data = {}

        name = generator.xpath('./GeneratorName/text()')
        fueltype = generator.xpath('./FuelType/text()')
        outputs = generator.xpath('./Outputs/Output') #xpath path to all the output tags in the outputs tag found in the current generator 
        capabilities = generator.xpath('./Capabilities/Capability')
        capacities = generator.xpath('./Capacities/AvailCapacity')

        for output in outputs:
            hour = output.xpath('./Hour/text()')
            energy_mw = output.xpath('./EnergyMW/text()')
            if energy_mw:
                output_data[int(hour[0])] = int(energy_mw[0])
            else:
                output_data[int(hour[0])] = 'N/A'

        for capability in capabilities:
            hour = capability.xpath('./Hour/text()')
            energy_mw = capability.xpath('./EnergyMW/text()')
            if energy_mw:
                capability_data[int(hour[0])] = int(energy_mw[0])
            else:
                capability_data[int(hour[0])] = 'N/A'

        for capacity in capacities:
            hour = capacity.xpath('./Hour/text()')
            energy_mw = capacity.xpath('./EnergyMW/text()')
            if energy_mw:
                capacity_data[int(hour[0])] = int(energy_mw[0])
            else:
                capacity_data[int(hour[0])] = 'N/A'

        data.append({
            gen_count: {
                'name': name[0],
                'fueltype': fueltype[0],
                'outputs': output_data,
                'capabilities': capability_data,
                'capacities': capacity_data
            }
        })

        gen_count += 1

        with open('./output/supply_by_generator_hourly.json', 'w') as file:
            json.dump(data, file, indent=4)

    return f'{gen_count} generators found. Returned JSON with hour intervals for {current_year}/{current_month}/{current_day}'
        
@app.get('/price/zonal')
def get_zonal_price():
    file_response = get_link(PRICE_URL_ZONAL, 'PUB_RealtimeZonalEnergyPrices.xml')
    tree = parse_xml(file_response)

    data = []
    zones = tree.xpath('//TransactionZone')

    for zone in zones:
        interval_data = {}

        name = zone.xpath('./ZoneName/text()')
        intervals = zone.xpath('./IntervalPrice')

        for interval in intervals:
            num = interval.xpath('./Interval/text()')
            zonal_price = interval.xpath('./ZonalPrice/text()')
            energy_loss_price = interval.xpath('./EnergyLossPrice/text()')
            energy_cong_price = interval.xpath('./EnergyCongPrice/text()')

            interval_data[int(num[0])] = {
                'Zonal Price': float(zonal_price[0]) if zonal_price else None, 
                'Energy Loss Price': float(energy_loss_price[0]) if energy_loss_price else None, 
                'Energy Congestion Price': float(energy_cong_price[0]) if energy_cong_price else None
            }

            delete_none(interval_data)

        data.append({
            name[0] : interval_data
        })

        with open('./output/zonal_pricing_realtime.json', 'w') as file:
            json.dump(data, file, indent=4)

    return 'OK'


    

        












    


