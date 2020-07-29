'''
Database.py:
- creates the databases needed for our application
- call this function from app.py by pasing the database names
'''

import sqlite3
import os
from sqlite3 import Error
from flask_sqlalchemy import SQLAlchemy

def CreateDatabase(db_names):
    dir_path = os.path.dirname(os.path.realpath(__file__))

    db_paths = [(dir_path + '/' + i + '.db') for i in db_names]

    for db_path in db_paths:
        sqlite3.connect(db_path)

    print("Databases are created")

def CreateTables(db):
    db.create_all()
    print("Tables are created")

