from flask import Flask, render_template, request, jsonify, abort, g, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from passlib.apps import custom_app_context as pwd_context
from flask_httpauth import HTTPBasicAuth
from datetime import datetime
from flask.wrappers import Response
from dotenv import load_dotenv
import os
import requests_cache
import requests
import json
import sqlite3
import click

load_dotenv()

requests_cache.install_cache('covid-api-cache', backend='sqlite', expire_after=36000)
covid_url_template = os.getenv('API_URL_TEMPLATE')
app = Flask(__name__)
auth = HTTPBasicAuth()

# Postgreslq database configuration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS') 
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI') 
app.debug = os.getenv('DEBUG') 
db = SQLAlchemy(app)
migrate = Migrate(app, db)

@app.cli.command("create_database")
# flask CLI command for heroku to Create Database
def create_database():
    db.create_all()
    admin = AccessType(id=1, title='admin')
    db.session.add(admin)
    user = AccessType(id=2, title='user')
    db.session.add(user)
    db.session.commit()

@app.cli.command("drop_database")
# flask CLI command for heroku to Drop Database
def drop_database():
    db.drop_all()

class User(db.Model):
# User class database model
    __tablename__ = 'user'    
    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(128), unique=False, nullable=False)
    password = db.Column(db.String(128), unique=False, nullable=False)
    country = db.Column(db.String(80), unique=False, nullable=False)
    access_id = db.Column(db.Integer, db.ForeignKey('access_type.id'), nullable=False, default=2)
    last_update = db.Column(db.DateTime, nullable=True, default=datetime.utcnow())

    def __init__(self, user_name, email, country, access_id):
        self.user_name = user_name
        self.country = country
        self.email = email
        self.access_id = access_id

    def hash_password(self, password):
        self.password = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password)

class AccessType(db.Model):
# AccessType class database model
    __tablename__ = 'access_type'    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), unique=True, nullable=False)

    def __init__(self, id, title):
        self.id = id
        self.title = title

class Stats:
# Stats class represents returned statistics from api
    def __init__(self, country, date, cases, deaths, recovered):
    # Creates a new instance of Stats class
        self.country = country
        self.date = date
        self.cases = cases
        self.deaths = deaths
        self.recovered = recovered

@app.route('/')
@app.route('/home')
def home():
# API home page or index page
    return render_template("home.html")

@app.route('/users', methods=['GET'])
# GET request to return all registered users in JSON format
def get_users():
    all_users = User.query.all()
    result = []
    if len(all_users) > 0:
        for user in all_users:
            current_user = {}
            current_user['user_name'] = user.user_name
            current_user['country'] = user.country
            current_user['email'] = user.email
            current_user['last_update'] = user.last_update
            current_user['access_id'] = user.access_id
            result.append(current_user)
    return jsonify(result)

@app.route('/users/add', methods=['POST'])
# POST request to add a new user to the database
def add_user():
    user_data = request.get_json()
    if len(user_data['user_name']) == 0 or len(user_data['email']) == 0 or len(user_data['country']) == 0 or len(user_data['password']) == 0:
        abort(Response('400: missing arguments'))
    if User.query.filter_by(user_name = user_data['user_name']).first() is not None:
        abort(Response('400: user already exists'))
    user = User(user_name=user_data['user_name'],
                email=user_data['email'],
                country=user_data['country'],
                access_id=user_data['access_id'])
    user.hash_password(user_data['password'])
    db.session.add(user)
    db.session.commit()
    return(Response('201: user added'))

@app.route('/users/update', methods=['PUT'])
# PUT request to update an existing user in the database
@auth.login_required
def update_user():
    if g.user.access_id == 1:
        user_data = request.get_json()
        if len(user_data['user_name']) == 0 or len(user_data['email']) == 0 or len(user_data['country']) == 0:
            abort(Response('400: missing arguments'))
        user = User.query.filter_by(user_name = user_data['user_name']).first()
        if user is None:
            abort(Response('404: user not found'))
        user.email = user_data['email']
        user.country = user_data['country']
        db.session.commit()
        return(Response('204: user updated'))
    else:
        return(Response('401: unauthorized user'))

@app.route('/users/delete/<user_name>', methods=['DELETE'])
# DELETE request to delete an existing user from the database
@auth.login_required
def delete_user(user_name):
    if g.user.access_id == 1:
        user = User.query.filter_by(user_name = user_name).first()
        if user is None:
            return(Response('404: user not found'))
        else:
            db.session.delete(user)
            db.session.commit()
            return(Response('200: user deleted'))
    else:
        return(Response('401: unauthorized user'))

@auth.verify_password
# User authentication function
def verify_password(username, password):
    user = User.query.filter_by(user_name = username).first()
    if not user or not user.verify_password(password):
        return False
    g.user = user
    return True

@auth.login_required
# User authorization function
def login_required(user_name, password):
    if verify_password(user_name, password):
        user = User.query.filter_by(user_name = user_name).first()
        if not user.access_id == 1:
            return False
        return True

@app.route('/users/login', methods=['GET', 'POST'])
# User login, if successful returns the lastest statistics for their country
def login():
    if request.method == 'GET':
        return render_template("login.html"), 200
    if request.method == 'POST':
        user_name = request.form['user_name']
        password = request.form['password']
        if len(user_name) == 0 or len(password) == 0:
            abort(Response('400: missing arguments'))
        if verify_password(user_name, password):
            user = User.query.filter_by(user_name = user_name).first()
            country = user.country
            user.last_update = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('get_stats_latest',country = country))
        else:
            return(Response('Failed login'))

@app.route('/stats/latest/<country>', methods = ['GET'])
# GET request to return latest covid-19 statistics by country from covid19api
def get_stats_latest(country):
    country = request.args.get('country', country)
    covid_url = covid_url_template.format(country = country)
    response = requests.get(covid_url)
    if response.ok:
        data = response.json()[len(response.json())-1]
        stats = Stats(str(data['Country']),
                    str(data['Date']),
                    str(data['Confirmed']),
                    str(data['Deaths']),
                    str(data['Recovered']))
        return render_template("stats.html", stats = stats), response.status_code
    else:
        return str(response.json()['message']), response.status_code

if __name__ == '__main__':
    app.run(threaded=True, port=5000)
