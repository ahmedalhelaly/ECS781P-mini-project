# Overview:
It is a simple app created as a Mini-Project for Cloud Computing module @QMUL-EECS Big Data Science MSc. programme.
The app enables you to register with your username, email and country. Once you successfully log in, you will be redirected to a simple HTML page with latest statistics in your country.

# How it works?
This is a Flask app so the code is written in Python. The database used is PostgresQL and SQLAlchemy is used as an ORM library. User authentication and authorization is implemented using access_types: 1 | admin & 2 | user. Only and admin can update and delete users. Passwords are hashed before saving in database and not as plain text.
External API used for retreiving covid 19 statistics can be found here: https://covid19api.com/ 

# RESTful Services:
### 1- GET
To retrieve all registered users in JSON format.
```
/users
```
To return latest covid-19 statistics by country from covid19api
```
/stats/latest/<country>
```
### 2- POST
To register a new user, data sent in the body in JSON format.
```
/users/add
```
```
{
    "user_name": "user_name",
    "password": "password",
    "email": "email",
    "country": "country",
    "access_id": 2
}
```
### 3- PUT
To update an existing user, data sent in the body in JSON format.
```
/users/update
```
```
{
    "user_name": "user_name",
    "password": "password",
    "email": "email",
    "country": "country",
    "access_id": 2
}
```
### 4- DELETE
To delete a user using their username.
```
/users/delete/<user_name>
```
