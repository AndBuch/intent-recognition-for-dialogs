# For FLASK-server
from flask import Flask, render_template, url_for, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import emit, SocketIO

import atexit

# For time
import time
from datetime import datetime

# For datahandling
import os
import io
import uuid
import csv
from queue import Queue

# For multithreading
from threading import Thread

# For opening the audio file
import wave
import scipy.io.wavfile as wav_stats

#custom python files
import database_custom
import audio_transcription_ibm
import intent_recognition
import arguments
import diarization
import model
from model import GermanBertMultiClassificationMultilingual     # must be imported separately to main(), otherwise we will get a .pickle error when loading the pretrained model

# Import DNN model-specific libraries
from pytorch_pretrained_bert import BertTokenizer, BertConfig
from pytorch_pretrained_bert import BertAdam, BertForSequenceClassification, BertModel
from transformers import AutoModel, AutoTokenizer

from pyannote.core import Segment
from pyannote.audio.features import RawAudio
import torch


'''
----------------------------------------------------------------------------------
Load Configurations
----------------------------------------------------------------------------------
'''

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

# Directory path
dir_path = os.path.dirname(os.path.realpath(__file__))

# Get Arguments class, which stores the basic information
args = arguments.Arguments()

# Define app/ reference file
app = Flask(__name__)
app.secret_key = "hello"
socketio = SocketIO(app)


def LoadConfigs():
    
    # Load the pipeline for the offline speaker diarization
    pipeline = torch.hub.load('pyannote/pyannote-audio', 'dia')

    # Load the tokenizer for later tokenizing the queries. 
    if args.model_type == "bert-base-german-cased":
        tokenizer = AutoTokenizer.from_pretrained("bert-base-german-cased")
                
    elif args.model_type == "bert-base-multilingual-uncased":
        tokenizer = BertTokenizer.from_pretrained("bert-base-multilingual-uncased")

    # Load model-class, which instantiates a new model and includes the Inference-function
    model_instance = model.Model(args)

    return pipeline, tokenizer, model_instance


'''
----------------------------------------------------------------------------------
Set-up Databases
----------------------------------------------------------------------------------
'''
# Define the names of the databases and create the databases (saved into same directory as app.py)
db_names = ['main', 'user', 'audio','transcript']
db_keys = {'user', 'audio', 'transcript'}

# Bind databases to application
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'             # first database to connect to
app.config['SQLALCHEMY_BINDS'] = {'user': 'sqlite:///user.db',          # dictionary that holds additional databases
                                'audio': 'sqlite:///audio.db',
                                'transcript': 'sqlite:///transcript.db'
                                }       
db = SQLAlchemy(app)                                                # initalize DB with app

# Create tables and their columns
class Main(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))           # Reference to users
    audio_id = db.Column(db.Integer, db.ForeignKey('audio.id'))
    transcript_id = db.Column(db.Integer, db.ForeignKey('transcript.id'))
    date_created  = db.Column(db.DateTime, default = datetime.utcnow)
 
    def __repr__(self):
        return self.id

class User(db.Model):
    __bind_key__ = 'user'
    id = db.Column(db.Integer, primary_key = True)
    users = db.Column(db.String(200), nullable = False)
    password = db.Column(db.String(200), nullable = False)
    date_created  = db.Column(db.DateTime, default = datetime.utcnow)
    
    main_id = db.relationship('Main', backref = 'user', lazy = True)
    
    def __repr__(self):
        return self.id


class Audio(db.Model):
    __bind_key__ = 'audio'
    id = db.Column(db.Integer, primary_key = True)
    audio_name = db.Column(db.String(200), nullable = False)
    duration = db.Column(db.Float, nullable = False)
    date_created  = db.Column(db.DateTime, default = datetime.utcnow)
    
    main_id = db.relationship('Main', backref = 'audio', lazy = True)

    def __repr__(self):
        return self.id
    

class Transcript(db.Model):
    __bind_key__ = 'transcript'
    id = db.Column(db.Integer, primary_key = True)
    transcript_name = db.Column(db.String(200), nullable = False)
    speakers = db.Column(db.Integer, nullable = False)
    date_created  = db.Column(db.DateTime, default = datetime.utcnow)
    date_modified = db.Column(db.DateTime, default = datetime.utcnow)
    
    main_id = db.relationship('Main', backref = 'transcript', lazy = True)

    def __repr__(self):
        return self.id


 
'''
----------------------------------------------------------------------------------
INDEX-Page
----------------------------------------------------------------------------------
'''
@app.route('/', methods = ['POST', 'GET'])

# Define the functions for the index page
def index():

    if request.method == 'POST':
        
        task_content = request.form['content']
        new_task = Main(content = task_content)

        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect('/')

        except:
            return "There was an issue with your request"

    else:
        tasks = Main.query.order_by(Main.date_created).all()
        return render_template('index.html', tasks = tasks)


    return render_template('index.html')


'''
----------------------------------------------------------------------------------
HOME-Page
----------------------------------------------------------------------------------
'''
@app.route('/home', methods = ['POST', 'GET'])

# Define the functions for the home page
def home():

    if request.method == 'POST':
        
        user = request.form['user']
        password = request.form['password']
        session['user'] = user
        session['password'] = password

        return redirect(url_for("portallogin"))

    
    else:
        tasks = Main.query.order_by(Main.date_created).all()
        return render_template('home.html')


    return render_template('home.html')

'''
----------------------------------------------------------------------------------
PORTAL-Login Procedure
----------------------------------------------------------------------------------
'''
@app.route('/portallogin', methods = ['POST', 'GET'])

# Define the functions for the portal page
def portallogin():

    if "user" in session:

        user = session["user"]
        password = session['password']

        # Check if user is in database and get first row of database and select the password
        found_user = User.query.filter_by(users = user).first()

        if found_user and password == found_user.password:
            session["login"] = True
            return redirect(url_for('portalrecord'))

        else:
            return redirect(url_for('home'))

    else:
        return redirect(url_for('home'))


'''
----------------------------------------------------------------------------------
PORTAL-Dialog Player Page
----------------------------------------------------------------------------------
'''
@app.route('/portal_record', methods = ['POST', 'GET'])

# Define the functions for the portal page
def portalrecord():

    if "user" in session and session["login"] == True:
        return render_template('portal.html')

    else:
        return redirect(url_for('home'))

@app.route('/uploads', methods=['POST'])
def save_audio():
    print("got new audio file")
    rawAudio = request.get_data()
    audioFile = open('RecordedFile.wav', 'wb')
    audioFile.write(rawAudio)
    audioFile.close()

'''
----------------------------------------------------------------------------------
PORTAL-Dialog Player Page
----------------------------------------------------------------------------------
'''
@app.route('/portal_dialog', methods = ['POST', 'GET'])

# Define the functions for the portal page
def portaldialog():

    if "user" in session and session["login"] == True:
        return render_template('portal_dialog player.html')

    else:
        return redirect(url_for('home'))


'''
----------------------------------------------------------------------------------
PORTAL-Statistics Page
----------------------------------------------------------------------------------
'''
@app.route('/portal_statistics', methods = ['POST', 'GET'])

# Define the functions for the portal page
def portalstatistics():

    if "user" in session and session["login"] == True:
        return render_template('portal_statistics.html')

    else:
        return redirect(url_for('home'))


'''
----------------------------------------------------------------------------------
PORTAL-Intent Checker Page
----------------------------------------------------------------------------------
'''
@app.route('/portal_check', methods = ['POST', 'GET'])

# Define the functions for the portal page
def portalcheck():

    if "user" in session and session["login"] == True:
        return render_template('portal_intent checker.html')

    else:
        return redirect(url_for('home'))


'''
----------------------------------------------------------------------------------
PORTAL-Logout Procedure
----------------------------------------------------------------------------------
'''
@app.route('/portallogout', methods = ['POST', 'GET'])

# Define the functions for the portal page
def portallogout():

    session.pop("user", None)
    return redirect(url_for('home'))


'''
----------------------------------------------------------------------------------
AUDIO-Recorder
----------------------------------------------------------------------------------
'''
@socketio.on('start-recording')
def start_recording(options):
    
    """Start recording audio from the client."""
    print('Recording started...')
    
    # Set parameter in session to recording
    session['recording'] = True

    # Create two new audio files in folder /audio, i.e the audio file and its chunks
    id = uuid.uuid4().hex  # server-side filename
    session['wavename'] = id + '.wav'
    session['audiopath'] = dir_path + '/audio/' + session['wavename']
    audio_write = wave.open(session['audiopath'], 'wb')
    
    # Set audio configuration
    session['channels'] = options.get('numChannels', 1)
    session['samplewidth'] = options.get('bps', 16) // 8
    session['framerate'] = options.get('fps', 44100)

    # Implement configuration for audio files
    audio_write.setnchannels(session['channels'])
    audio_write.setsampwidth(session['samplewidth'])
    audio_write.setframerate(session['framerate'])
    session['wavefile'] = audio_write

    # Start transcription as long as session['transcripe'] = True
    transcription = audio_transcription_ibm.IBM_STT()
    session['transcription'] = transcription
    print('Started the websocket connection')

    # Save all current transcriptions into a buffer, which is read by intent_recognition.py
    session['transcript_buffer'] = list()
    session['speaker_buffer'] = list()

    # Create a new instance of the intent_recognition class
    session['intent_recognition'] = intent_recognition.IntentRecognition(tokenizer, args, model_instance)

    # Create a new diarization instance
    session['speakers'] = diarization.Diarization(pipeline, session['channels'], session['samplewidth'], session['framerate'])


@socketio.on('write-audio')
def write_audio(audio_chunk):

    """Write a chunk of audio from the client."""

    # Update the buffer of the transcription with the latest audio chunk (FIFO principle)
    session['transcription'].UpdateBuffer(audio_chunk)

    # Check whether there is already a transcription available and if so, retrieve it
    session['transcript_buffer'] = session['transcription'].UpdateTranscriptBuffer(session['transcript_buffer'])

    # Get the current speakers using a buffer as well
    session['speaker_buffer'] = session['transcription'].UpdateSpeakerBuffer(session['speaker_buffer'])
    session['speaker_buffer'] = session['speakers'].GetSpeakers(session['speaker_buffer'], session['audiopath'])

    # Update the input-queue for the model
    session['transcript_buffer'] = session['intent_recognition'].UpdateInputQueue(session['transcript_buffer'])

    # Extend the audio frame with the latest audio chunk
    session['wavefile'].writeframes(audio_chunk)
    

@socketio.on('end-recording')
def end_recording():
    
    """Recording stopped..."""
    print('Recording ended...')
    
    # End the transcription by calling StopTranscript()
    final_transcript, speaker_transcript, speaker_ids = session['transcription'].StopTranscript()
    num_speakers = len(speaker_ids)

    print(type(speaker_transcript))
    print(speaker_transcript)

    # Save transcripts as csv-files
    transcript_name  = session['wavename'][0:(len(session['wavename']) - 4)] + '.csv'
    transcript_path  = dir_path + '/transcripts/' + transcript_name
    csv_file = open(transcript_path, "w")
    csv_writer = csv.DictWriter(csv_file, fieldnames = ["speaker", "sentence"])
    csv_writer.writeheader()
    csv_writer.writerows(speaker_transcript)
    csv_file.close()
    
    # Save and close .wav-file
    emit('add-wavefile', audio_path = dir_path + '/audio/' + session['wavename'])
    session['wavefile'].close()

    (audio_rate, audio_sig) = wav_stats.read(session['audiopath'])
    audio_duration = len(audio_sig) / float(audio_rate)
    
    # Add audio and transcript to database
    database_custom.UpdateRecording(Main, Audio, Transcript, User, db, session['user'], session['wavename'], audio_duration, transcript_name, num_speakers)
    
    # Get items of input queue
    session['intent_recognition'].GetItems()

    # Free up session
    del session['wavefile']
    del session['wavename']
    del session['audiopath']
    del session['channels']
    del session['samplewidth']
    del session['framerate'] 
    
'''
----------------------------------------------------------------------------------
For debugging
----------------------------------------------------------------------------------
'''

if __name__ == "__main__":
    
    # Create the database and the tables using the functions in database.py
    database_custom.CreateDatabase(db_names)
    database_custom.CreateTables(db) 

    # Load all the models
    pipeline, tokenizer, model_instance = LoadConfigs()

    # Actually start and run the application
    socketio.run(app, use_reloader = False , debug = True )
    


@atexit.register
def goodbye():
    print("You are now leaving the Python sector.")