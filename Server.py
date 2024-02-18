from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from Logger import *
from datetime import datetime, timedelta
from dotenv import load_dotenv
from random import choice

import requests
import os
import json


# Load environment variables
load_dotenv()

# Start log config
Logger.setup_logging()

# Initialize Flask extensions
db = SQLAlchemy()
migrate = Migrate()


class Config:
    """Flask application config class."""
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PWD')}@{os.getenv('DB_HOST')}:5432/{os.getenv('DB_NAME')}"


class Earthquakes(db.Model):
    """
    Earthquake model for storing earthquake data.
    """
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    depth = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(4), nullable=False)
    magnitude = db.Column(db.Float, nullable=False)
    place = db.Column(db.String(250), nullable=False)

    @classmethod
    def create_from_json(cls, json_data):
        """
        Creates an Earthquake record from JSON data, avoiding duplicates based on date, latitude, longitude, and magnitude.

        Param:
            json_data (dict): A dictionary containing the earthquake data comes from Scraper.

        """
        # Convert date string from JSON data to a datetime object.
        date_str = json_data['Date']
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

        # Check if an earthquake record already exists.
        existing_quake = cls.query.filter_by(
            date=date_obj,
            latitude=json_data['Latitude'],
            longitude=json_data['Longitude'],
            magnitude=json_data['Magnitude']
        ).first()

        if not existing_quake:
            # If not exist, create a new Earthquake record.
            earthquake = cls(
                date=date_obj,
                latitude=json_data['Latitude'],
                longitude=json_data['Longitude'],
                depth=json_data['Depth(Km)'],
                type=json_data['Type'],
                magnitude=json_data['Magnitude'],
                place=json_data['Location']
            )
            db.session.add(earthquake)
            logging.info("Earthquake data successfully saved.")
        else:
            # If exists, show message.
            logging.info(f"This earthquake data is already recorded with ID {existing_quake.id}.")


class DatabaseManager:
    """Class to handle database operations."""

    @staticmethod
    def add_earthquake(json_data):
        """Adds new earthquake data to the database.
        param: json_data: dict containing earthquake data.
        """
        try:
            latest_record = DatabaseManager.get_latest_earthquake()
            max_date = latest_record.date if latest_record else None
            new_data_added = False
            for quake_data in json_data:
                date_str = quake_data['Date']
                date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                if not max_date or date_obj > max_date:
                    Earthquakes.create_from_json(quake_data)
                    new_data_added = True
            db.session.commit()

            if new_data_added:
                logging.info("New data has been added")
            else:
                logging.info("There is no new data")

        except Exception as e:
            db.session.rollback()
            logging.info("Transaction has been rollbacked.")

    @staticmethod
    def get_all_earthquakes():
        """Retrieves all earthquake records from the database.
        return: List of Earthquake instances.
        """
        return Earthquakes.query.order_by(Earthquakes.date.desc()).all()

    @staticmethod
    def get_latest_earthquake():
        """Retrieves the most recent earthquake record.
        return: Latest Earthquake instance.
        """
        return Earthquakes.query.order_by(Earthquakes.date.desc()).first()

    @staticmethod
    def last_quake_status():
        """Determines the status of the latest earthquake
        return: A dictionary containing the status message, latest earthquake information and the image_url, if any.
        """
        latest_date_record = DatabaseManager.get_latest_earthquake()
        status_data = {}
        if latest_date_record:
            max_date = latest_date_record.date
            current_time = datetime.utcnow() + timedelta(hours=3)
            time_difference = current_time - max_date
            waiting_time = int(os.getenv('SCRAPING_TIME_INTERVAL'))
            if time_difference > timedelta(seconds=waiting_time):
                status_data['message'] = "Belirlenen Zaman Aralığında Deprem Olmamıştır."
                status_data['quake_info'] = None
            else:
                status_data['message'] = "Yeni Deprem Oldu."
                status_data['quake_info'] = latest_date_record
                image_url = APIManager.get_unsplash_photo(latest_date_record.place)
                status_data['image_url'] = image_url
        else:
            logging.info("There is no record")
            return None
        return status_data


class APIManager:
    """ For API managing class."""

    @staticmethod
    def get_unsplash_photo(query):
        """ Fetches a photo from Unsplash based on the query.
        param: query: str representing the search query key.
        return: URL of the first photo if successful, None otherwise.
        """
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query,
            "client_id": os.getenv('UNPLASH_API_KEY'),
            "page": 1,
            "per_page": 5
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            results = response.json()['results']
            if results:
                return results[0]['urls']['regular']
        return None


def create_app():
    """ Function to create and configure the Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    @app.route('/api/earthquakes', methods=['POST'])
    def add_earthquake_page():
        """ Add earthquake data. """
        try:
            raw_data = request.get_json()
            json_data = json.loads(raw_data)
            DatabaseManager.add_earthquake(json_data)
            return jsonify({"successful"}), 200
        except Exception as e:
            return jsonify({"error": str(e)})

    @app.route('/home', methods=['GET'])
    def home_page():
        """ Display home page with earthquake data."""
        all_earthquakes = DatabaseManager.get_all_earthquakes()
        status_data = DatabaseManager.last_quake_status()

        # Check the database is empty or not.
        if status_data is None:
            status_data = {
                'message': "Durum Verileri Alınamadı. Tekrar Deneyiniz.",
                'quake_info': None
            }

        if all_earthquakes:
            # Choice random earthquake from database.
            random_earthquake = choice(all_earthquakes)

            # Find relevant image from API using EQ place name.
            image_url = APIManager.get_unsplash_photo(random_earthquake.place)
        else:
            random_earthquake = None
            image_url = None

        # Send variables to HTML file.
        content = {
            'status_data': status_data,
            'earthquakes': all_earthquakes,
            'random_earthquake': random_earthquake,
            'image_url': image_url
        }

        return render_template('index.html', **content)

    return app
