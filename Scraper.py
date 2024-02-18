from bs4 import BeautifulSoup
from Logger import *
from dotenv import load_dotenv

import requests
import json
import os


# Start log config
Logger.setup_logging()
load_dotenv()


class Scraper:
    def __init__(self):
        # Initialize the scraper with a URL to scrape data from
        self.url = os.getenv('TARGET_URL')

    def fetch_quake_data(self):
        """
        Fetches earthquake data from the specified URL and formats it as JSON.

        return: A JSON string containing a list of earthquakes, where each earthquake is represented as a dictionary
                 with keys for date, latitude, longitude, depth, type, magnitude, and location.
        """
        # Make a GET request to the URL.
        response = requests.get(self.url)
        if not response.ok:
            logging.error("Scraper couldn't response the page")
            return None

        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        earthquakes = []

        # Skip the first row (headers) and iterate through each row in the table.
        for row in soup.find_all('tr')[1:]:
            cells = row.find_all('td')
            earthquake = {
                'Date': cells[0].text.strip(),
                'Latitude': cells[1].text.strip(),
                'Longitude': cells[2].text.strip(),
                'Depth(Km)': cells[3].text.strip(),
                'Type': cells[4].text.strip(),
                'Magnitude': cells[5].text.strip(),
                'Location': cells[6].text.strip(),
            }
            earthquakes.append(earthquake)

        # Convert the list of dictionaries to a JSON string.
        json_data = json.dumps(earthquakes, ensure_ascii=False, indent=4)
        return json_data

    def post_quake_data(self):
        """
        Posts the fetched earthquake data to a specified endpoint as JSON.

        This function fetches the earthquake data, then sent post request this data to a specified
        endpoint.

        """
        json_data = self.fetch_quake_data()
        headers = {'Content-Type': 'application/json'}

        try:
            # Send Post request the earthquake data to the specified endpoint.
            response = requests.post('http://flask_container:5000/api/earthquakes', json=json_data, headers=headers)
            logging.info(f"{response.status_code} request is ok")
        except requests.RequestException as e:
            logging.error(f'An error occurred while requesting flask container: {response.status_code}')



