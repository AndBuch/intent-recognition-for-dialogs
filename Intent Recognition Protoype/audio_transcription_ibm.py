# For IBM Speech-to-Text
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.websocket import RecognizeCallback, AudioSource

# For data handling
from queue import Queue
import json
import configparser
import os

# For multithreading
import threading
from threading import Thread

# For time
import time


'''
----------------------------------------------------------------------------------
Callback-Class
----------------------------------------------------------------------------------
'''
# A callback class to process various streaming STT events
class NewRecognizeCallback(RecognizeCallback):
    def __init__(self):
        RecognizeCallback.__init__(self)
        
        # Save current transcripts and speakers
        self.transcript = None
        self.transcript_queue = list()
        self.current_speaker = None
        self.transcript_queue_all = list()

        # Save ongoing transcripts
        self.final_transcript = list()
        self.speakers = list()
        self.speaker_ids = list()

    def on_transcription(self, transcript):
        # print('transcript: {}'.format(transcript))
        pass

    def on_connected(self):
        print('Connection was successful')
        pass

    def on_error(self, error):
        # print('Error received: {}'.format(error))
        pass

    def on_inactivity_timeout(self, error):
        # print('Inactivity timeout: {}'.format(error))
        pass

    def on_listening(self):
        # print('Service is listening')
        pass

    def on_hypothesis(self, hypothesis):
        # print('hypothesis: {}'.format(hypothesis))
        pass

    def retrieve_speakers(self, data):
        
        speaker_labels = data['speaker_labels']
        speakers_positions = [item['speaker'] for item in speaker_labels]
        speakers_unique = list(set(speakers_positions)) # get only the speakers

        # Normally, the first speakers are '0', except for monologues
        if len(speakers_unique) > 1:
            
            first_speaker = speakers_positions[0]
            modified_positions = list()
            
            # Check which is the first speaker ID (in case that they change)
            for i in speakers_positions:
                if i != first_speaker:
                    modified_positions.append(i)

            next_speaker = modified_positions[0]

            # Now, let's change all ID of the first_speaker to the next_speaker
            for n, i in enumerate(speakers_positions):
                if i == first_speaker:
                    speakers_positions[n] = next_speaker

            # Also, you have to delete the "first_speaker" from the speakers_unique list
            speakers_unique.pop(0)
            

        speakers_sentences = list()
        transcript = self.transcript.split()

        # Check if there is more than one word in the speakers_positions. Often IBM will transmit the first word again!
        if len(speakers_positions) > 1:

            # Get all indices in transcript of every speaker in the list
            for speaker in speakers_unique:
                positions = [ i for i in range(len(speakers_positions)) if speakers_positions[i] == speaker ]
                sentence = list()

                # Sometimes, the STT-engine does not recognize any words, then catch it.
                try:
                    for word in positions:
                        sentence.append(transcript[word])

                except:
                    pass
                
                # Converts the list to a string
                sentence_string = ' '
                sentence_string = sentence_string.join(sentence)

                # Save it to speakers_sentences at function-level
                self.speakers.append({'speaker': speaker, 'sentence': sentence_string})
                self.transcript_queue.append({'speaker': speaker, 'sentence': sentence_string})

                # Print output
                print("Speaker {0}: {1}".format(speaker, sentence_string))

            # Finally, add the speakers_sentences to the global list speakers
            # self.speakers.append(speakers_sentences)

            # Check if speaker_ids are already in self.num_speakers. If not, update num_speakers
            for speaker in speakers_unique:
                if speaker not in self.speaker_ids:
                    self.speaker_ids.append(speaker)


    def on_data(self, data):
        
        # Speaker labels are returned after the transcript is final
        if "speaker_labels" in data:
            self.retrieve_speakers(data)

        # For all other, regular outputs, follow the below procedure
        else:
            
            # Only write final transcripts
            if data['results'][0]['final']:
                self.transcript = data['results'][0]['alternatives'][0]['transcript']
                #print('Transcript: {0}'.format(self.transcript))
                #print(data)
                    
                # Save all final transcripts into the list final_transcript
                self.final_transcript.append(data['results'][0]['alternatives'][0]['transcript'])

                # Save the entire output to the transcript_queue_all which will be examined everytime a write-event occurs
                self.transcript_queue_all.append(data)
            

    def on_close(self):
        print("Connection closed")
        pass


'''
----------------------------------------------------------------------------------
IBM Speech-to-Text class:
- initiates a new websocket connection to the IBM Cloud using the defined 
authentiation parameters (must be updated, if user changes)
- creates a new callbfack object, which establishes the websocket connection

----------------------------------------------------------------------------------
'''

class IBM_STT(object):

    def __init__(self):
    
        # Set the configuration and authentication parameters
        self.RATE = 44100
        self.MODEL = 'de-DE_BroadbandModel'
        self.apikey = 'XlnYEDrboVWooaf7ewbb39M7VMN50PVyQWk9ZBq9KFT_'
        self.url = 'https://api.eu-de.speech-to-text.watson.cloud.ibm.com/instances/3253a885-9bd2-4daa-9cc2-449d9b2951ac'
        
        # Authenticate against IBM Cloud
        self.authenticator = IAMAuthenticator(self.apikey)
        self.speech_to_text = SpeechToTextV1(authenticator=self.authenticator)
        self.speech_to_text.set_service_url(self.url)

        # Create a buffer (= queue) and put it to the AudioSource
        self.buffer = Queue()
        self.audio_source = AudioSource(self.buffer, True, True)
        
        # Create a new Callback object
        self.callback = NewRecognizeCallback()

        # Start the Websocket-Thread
        self.stt_stream_thread = Thread(
            target=self.speech_to_text.recognize_using_websocket,
            kwargs={
            'audio': self.audio_source,
            'content_type': 'audio/l16; rate={}'.format(self.RATE),
            'model' : self.MODEL,
            'recognize_callback': self.callback,
            'interim_results': True,
            'speaker_labels' : True,
            'split_transcript_at_phrase_end' : True
            }
        )

        self.stt_stream_thread.start()

    # This function updates the queue
    def UpdateBuffer(self, audio_frame):
        self.buffer.put(audio_frame)

    # This function updates the queue
    def UpdateTranscriptBuffer(self, transcript_buffer):

        # Check whether the transcript_queue is empty or not. If not, iterate over all transcripts and return them
        if len(self.callback.transcript_queue) > 0:
            
            for transcript in self.callback.transcript_queue:
                transcript_buffer.append(transcript)
            
            # Re-set transcript_queue
            self.callback.transcript_queue = list()

        return transcript_buffer


    # This function returns the entire current transcript disregarding the speakers
    def UpdateSpeakerBuffer(self, speaker_buffer):

        # Check whether the transcript_queue is empty or not. If not, iterate over all transcripts and return them
        if len(self.callback.transcript_queue_all) > 0:
            
            for data in self.callback.transcript_queue_all:
                speaker_buffer.append(data)
            
            # Re-set transcript_queue
            self.callback.transcript_queue_all = list()

        return speaker_buffer



    # Stop the transcription by ending the recording in audio_source
    def StopTranscript(self):
        self.audio_source.completed_recording()
        self.stt_stream_thread.join()

        return self.callback.final_transcript, self.callback.speakers, self.callback.speaker_ids

