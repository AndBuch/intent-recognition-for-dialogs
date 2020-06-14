'''
Database.py:
- creates the databases needed for our application
- call this function from app.py by pasing the database names
'''

# For SQLite
import sqlite3
from sqlite3 import Error
from flask_sqlalchemy import SQLAlchemy

# For datahandling
import os

def CreateDatabase(db_names):
    dir_path = os.path.dirname(os.path.realpath(__file__))

    db_paths = [(dir_path + '/' + i + '.db') for i in db_names]

    for db_path in db_paths:
        sqlite3.connect(db_path)

    print("Databases are created")

def CreateTables(db):
    db.create_all()
    print("Tables are created")


def UpdateRecording(Main, Audio, Transcript, User, db, user_name, audio_name, audio_duration, transcript_name, num_speakers):

    # Update the audio table
    audio_update = Audio(audio_name = audio_name, duration = audio_duration)
    db.session.add(audio_update)
    db.session.commit()

    # Update the transcript table
    transcript_update = Transcript(transcript_name = transcript_name, speakers = num_speakers)
    db.session.add(transcript_update)
    db.session.commit()

    # Select id of user by user_name
    user_id = User.query.filter_by(users = user_name).first()

    # Update the main table
    main_update = Main(user_id = user_id.id, audio_id = audio_update.id, transcript_id = transcript_update.id)
    db.session.add(main_update)
    db.session.commit()
    
    print('Recording and transcripts are saved into database...')


