"""Streams transcription of the given audio file."""
import io
import os
import time

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
from google.oauth2 import service_account
from google.cloud import speech_v1p1beta1

# just for testing
import inspect

class Transcription(object):

    def __init__(self, transcribe):
        
        self.transcribe = True
        self.audio = ''
        self.responses = list()
        self.speaker1 = list()
        self.speaker2 = list()

        # Get the credentials for Google Speech to Text
        self.cred_path = os.path.dirname(os.path.realpath(__file__)) + '/authentication/Intent Recognition-a05dea925a9e.json'
        self.credentials = service_account.Credentials.from_service_account_file(self.cred_path)


    def transcribe_single(self, audio_data):

        ''' Start transcription of the audio files by calling this function in app.py'''
        print('start transcribing single audio')

        # Set up a new speech client from the GCS library
        client = speech_v1p1beta1.SpeechClient(credentials = self.credentials)

        config = {
            'encoding' : enums.RecognitionConfig.AudioEncoding.LINEAR16,
            'sample_rate_hertz':44100,
            'language_code': 'de-DE',
            'enable_speaker_diarization': True,   
            'diarization_speaker_count': 2
        }
            
        audio = {"content": audio_data}

        try:
            responses = client.recognize(config, audio)

        except Exception as e:
            print(e)
            pass

        speaker_1 = list()
        speaker_2 = list()
        speaker_unk = list()

        for result in responses.results:
            # First alternative has words tagged with speakers
            alternative = result.alternatives[0]
            print(u"Transcript: {}".format(alternative.transcript))
            # Print the speaker_tag of each word
            for word in alternative.words:
                #print(u"Word: {}".format(word.word))
                #print(u"Speaker tag: {}".format(word.speaker_tag))
                if word.speaker_tag == 1:
                    speaker_1.append(word.word)

                elif word.speaker_tag == 2:
                    speaker_2.append(word.word)
                    
                else: 
                    speaker_unk.append(word.word)

            print("speaker 1: %s" % speaker_1)
            print("speaker 2: %s" % speaker_2)
            print("speaker unk: %s" % speaker_unk)

                

    def transcribe_audio(self):
        
        ''' Start transcription of the audio files by calling this function in app.py'''
        print('start transcribing')

        # Set up a new speech client from the GCS library
        client = speech.SpeechClient(credentials = self.credentials)
        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code='de-DE')
        streaming_config = types.StreamingRecognitionConfig(config=config, interim_results=True)

        # While transcribe (set in app.py) is True, check if list of audio files has any items
        while self.transcribe == True:

            # Check if audio list has any items, if so take the first item, send it to Google Cloud Speech to Text
            if len(self.audio) > 0:
                
                stream = [self.audio]
                request = (types.StreamingRecognizeRequest(audio_content=chunk)
                    for chunk in stream)

                try:
                    response = client.streaming_recognize(streaming_config, request)
                    print('transcribed')
                    self.responses.append(response)

                except Exception as e:
                    print(e)
                    pass

                self.audio = ''

                print(dir(response))

        for response in self.responses:
            
            # Once the transcription has settled, the first result will contain the
            # is_final result. The other results will be for subsequent portions of
            # the audio.
            print(dir(response))
            try:
                for line in response.results:
                    print(line)

            except Exception as e:
                print(e)
                pass


    def transcribe_all(self, audio_data):
        
        ''' Start transcription of the audio files by calling this function in app.py'''
        print('start transcribing all audio')

        # Set up a new speech client from the GCS library
        client = speech.SpeechClient(credentials = self.credentials)
        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=44100,
            language_code='de-DE',
            )

        streaming_config = types.StreamingRecognitionConfig(config=config)

        stream = [audio_data]
        
        request = (types.StreamingRecognizeRequest(audio_content=chunk)
            for chunk in stream)

        # print(request)

        try:
            responses = client.streaming_recognize(streaming_config, request)
            print('transcribed')

        except Exception as e:
            print(e)
            pass

        print(dir(responses))

        for response in responses:
        
            try:
                for result in response.results:
                    print(result)

            except Exception as e:
                print(e)
                pass
        

    def transcribe(audio):
        client = speech.SpeechClient()

        # In practice, stream should be a generator yielding chunks of audio data.
        stream = [audio_frame]
        requests = (types.StreamingRecognizeRequest(audio_content=chunk)
                    for chunk in stream)

        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code='de-')
        streaming_config = types.StreamingRecognitionConfig(config=config)

        # streaming_recognize returns a generator.
        responses = client.streaming_recognize(streaming_config, requests)

        for response in responses:
            # Once the transcription has settled, the first result will contain the
            # is_final result. The other results will be for subsequent portions of
            # the audio.
            for result in response.results:
                print('Finished: {}'.format(result.is_final))
                print('Stability: {}'.format(result.stability))
                alternatives = result.alternatives
                # The alternatives are ordered from most likely to least.
                for alternative in alternatives:
                    print('Confidence: {}'.format(alternative.confidence))
                    print(u'Transcript: {}'.format(alternative.transcript))