"""Streams transcription of the given audio file."""
import io
import time
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types

class Transcription(object):

    def __init__(self, transcribe):
        self.transcribe = True
        self.i = 0
        self.audio = list()

    def transcribe_audio(self):
        
        print(self.transcribe)
        print('start transcribing')

        start_time = time.time()

        i = 0

        while self.transcribe == True:

            # Check if list has any items
            if len(self.audio) > 0:
                i += 1
                self.audio.pop(0)
                
        print("number of frames %s" %i)
        print(len(self.audio))
        
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