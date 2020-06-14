import os
import wave
import torch

# For speaker diarization
from pyannote.core import Segment
from pyannote.audio.features import RawAudio


'''
OLD code
#from pyAudioAnalysis.pyAudioAnalysis import audioSegmentation as aS
def diarize_audio(path):
    path = path
    res = aS.speaker_diarization(path, 2)
    print(res)
'''

class Diarization(object):

    def __init__(self, pipeline, channels, bps, rate):

        # Set configurations
        self.transcripts = 0
        self.speakers_list = list()
        self.RATE = rate
        self.CHANNELS = channels
        self.BPS = bps

        # Save the beginning of the last transcript
        self.beginning_previous_transcript = 0

        # Count the number of speakers already identified. This helps to retrieve the time of the current speaker. 
        self.speaker_identified = 0

        # Save the concurring difference between end- and start-time to know the absolute position of the speaker in the audio
        self.time_difference = 0

        # Define pipeline for diarization
        self.pipeline = pipeline

        # Define a new chunk-audio file to save only the current frames needed for the speaker diarization
        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        self.chunk_path = self.dir_path + '/audio/chunk.wav'

    def GetSpeakers(self, transcript_data, wav_file):

        
        if len(transcript_data) > 0 :

            FILE = {'audio': wav_file}
            chunk_path = 'audio/chunk.wav'

            # Get the data inside transcript_data to access the dictionaries
            transcript_data = transcript_data[0]
            print(transcript_data['results'][0])
            num_words_transcript = len(transcript_data['results'][0]['alternatives'][0]['timestamps'])

            # Get the beginning and the end of the words, i.e. the seconds in the wav-file
            start_word = transcript_data['results'][0]['alternatives'][0]['timestamps'][0][1]
            end_word = transcript_data['results'][0]['alternatives'][0]['timestamps'][num_words_transcript-1][2]

            # Get the indices, i.e. the positions in the wav-file
            if self.transcripts == 0:
                start_index = 0
                start_word = 0

            else:
                start_index = self.beginning_previous_transcript

            # The end_index and also the start_index (see below) are the product of the position (in sec) and the frame rate (44100)
            end_index = self.RATE * end_word
            num_frames = int(end_index - start_index)
            print(type(num_frames))
            num_frames_r = int(round(num_frames))
            print(type(num_frames_r))

            # Read the audio frame using wave.read.setpos()
            with wave.open(wav_file, mode='rb') as wavread:
                wavread.setpos(start_index)
                audio_wav = wavread.readframes(int(num_frames_r))
                wavread.close()

            # Write the audio-snippet into a new frame. Otherwise, we would need to deal with the entire audio-file for diarization
            wavwrite = wave.open(self.chunk_path, mode = 'wb')
            wavwrite.setnchannels(self.CHANNELS)
            wavwrite.setsampwidth(self.BPS)
            wavwrite.setframerate(self.RATE)
            wavwrite.writeframes(audio_wav)
            wavwrite.close()
            
            # Instantiate the diarization
            diarization = self.pipeline({'audio': self.chunk_path})
            
            # Save the turns to the turn list
            turn_list = list()

            for turn, _, speaker in diarization.itertracks(yield_label=True):
                turn_list.append({'speaker' : speaker, 'start_time': (turn.start + self.time_difference) , 'end_time': (turn.end + self.time_difference)})

            # Only keep those speakers in diarziation that have not been previously identified
            for i in range(self.speaker_identified):
                turn_list.pop(i-1)

            print(turn_list)

            # Reset speaker_identified for the next transcript
            self.speaker_identified = 0
            self.speaker_identified = len(turn_list)

            # Update the beginning_previous_transcript for the next transcript
            self.beginning_previous_transcript = int(self.RATE * start_word)

            # Increase the counter
            self.transcripts += 1 
            self.time_difference = self.time_difference + (end_word - start_word)


        # Empty the list to prevent duplicate entries
        transcript_data  = list()

        return transcript_data



