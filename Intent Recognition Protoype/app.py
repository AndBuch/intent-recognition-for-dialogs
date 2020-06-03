from flask import Flask, render_template, url_for, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import uuid
import wave
from flask_socketio import emit, SocketIO

from datetime import datetime

import os

# For multithreading
from threading import Thread

# For audio
import speech_recognition as sr

#custom python files
import database_custom
import audio_transcription


# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

# Directory path
dir_path = os.path.dirname(os.path.realpath(__file__))

# Define app/ reference file
app = Flask(__name__)
app.secret_key = "hello"
socketio = SocketIO(app)

# Define the names of the databases and create the databases (saved into same directory as app.py)
db_names = ['main', 'user']
db_keys = {'user'}
database_custom.CreateDatabase(db_names)

# Bind databases to application
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'         # first database to connect to
app.config['SQLALCHEMY_BINDS'] = {'user': 'sqlite:///user.db'}      # dictionary that holds additional databases
db = SQLAlchemy(app)                                                # initalize DB with app

# Create tables and their columns
class Main(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    content = db.Column(db.String(200), nullable = False)               # String(length in character), nullable = can be empty?
    completed = db.Column(db.Integer, default = 0)
    date_created  = db.Column(db.DateTime, default = datetime.utcnow)   # Default = if entry is created automatically create datetime
 
    def __repr__(self):
        return '<Task %r>' %self.id

class User(db.Model):
    __bind_key__ = 'user'
    id = db.Column(db.Integer, primary_key = True)
    users = db.Column(db.String(200), nullable = False)
    password = db.Column(db.String(200), nullable = False)
    date_created  = db.Column(db.DateTime, default = datetime.utcnow)

database_custom.CreateTables(db)     # Create tables using the function in database.py

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
        return render_template('home.html', tasks = tasks)


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
    print('started recording')
    
    """Start recording audio from the client."""
    
    # Create two new audio files in folder /audio, i.e the audio file and its chunks
    id = uuid.uuid4().hex  # server-side filename
    session['wavename'] = id + '.wav'
    session['audiopath'] = dir_path + '/audio/' + session['wavename']
    session['chunkspath'] = dir_path + '/audio/' + id + '_chunks.wav'
    audio_write = wave.open(session['audiopath'], 'wb')
    audio_chunks = wave.open(session['chunkspath'], 'wb')
    
    # Set audio configuration
    session['channels'] = options.get('numChannels', 1)
    session['samplewidth'] = options.get('bps', 16) // 8
    session['framerate'] = options.get('fps', 44100)

    # Implement configuration for audio files
    audio_write.setnchannels(session['channels'])
    audio_write.setsampwidth(session['samplewidth'])
    audio_write.setframerate(session['framerate'])
    session['wavefile'] = audio_write

    audio_chunks.setnchannels(session['channels'])
    audio_chunks.setsampwidth(session['samplewidth'])
    audio_chunks.setframerate(session['framerate'])
    session['chunksfile'] = audio_chunks

    # Start transcription as long as session['transcripe'] = True
    transcription = audio_transcription.Transcription(True)
    session['transcription'] = transcription
    session['transcription'].transcribe = True
    t1 = Thread(target = session['transcription'].transcribe_audio)
    t1.start()
    print('going further')


@socketio.on('write-audio')
def write_audio(data):

    print("write data")
    """Write a chunk of audio from the client."""

    # Extend the audio frame with the new data
    session['wavefile'].writeframes(data)
    
    # Write the new data to our chunks-file, close it and open it for reading
    session['chunksfile'].writeframes(data)
    session['chunksfile'].close()
    
    read_chunks = wave.open(session['chunkspath'], 'rb')
    current_frames = read_chunks.readframes(2048)
    read_chunks.close()

    # Re-open chunks-file for future writing. For this, we have to define the writing-config again
    audio_chunks = wave.open(session['chunkspath'], 'wb')
    audio_chunks.setnchannels(session['channels'])
    audio_chunks.setsampwidth(session['samplewidth'])
    audio_chunks.setframerate(session['framerate'])
    session['chunksfile'] = audio_chunks

    # Finally, we add the new audio frames to the list of frames in our transcription class
    session['transcription'].audio.append(current_frames)

    
@socketio.on('end-recording')
def end_recording():
    print("end recording")
    
    """Stop recording audio from the client."""
    emit('add-wavefile', audio_path = dir_path + '/audio/' + session['wavename'])
    session['wavefile'].close()

    # Set transcribe to "False" in order to stop the while-loop in function transcribe()
    session['transcription'].transcribe = False
    
    # Free up session
    del session['wavefile']
    del session['chunksfile']
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
    socketio.run(app, debug=True)
