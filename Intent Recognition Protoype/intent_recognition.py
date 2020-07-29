# For data handling
from queue import Queue

import sys
import os
sys.stdout = open(os.devnull, 'w')

# For multithreading
import asyncio

# Import libraries for data handling
import torch
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
import pandas as pd
from keras.preprocessing.sequence import pad_sequences
from sklearn.model_selection import train_test_split
import numpy as np

from threading import Thread
import re

# Only for testing
import time


class IntentRecognition(object):

    def __init__(self, tokenizer, args, model_instance):
        
        # Iterim storage of data during data processing and inference
        self.input_queue = Queue()
        self.tokenized_queue = Queue()
        self.intent = list()
        
        # Must be set to False by app.py once the recording is finished
        self.recording = True
        self.inference = True
        
        # BERT Tokenizer and model instance
        self.tokenizer = tokenizer
        #self.embedding_model = SentenceTransformer('distiluse-base-multilingual-cased')
        self.model_instance = model_instance

        # Arguments class as passed from app.py
        self.args = args

        # Assign the thread to the class and define the sleep_thread variable
        self.start_intent_recognition = None
        self.sleep_thread = False


    # Clean the queries before passing them to the sentence embeddings
    def CleanQueries(self, query):
        
        # Remove cetrain strings
        query = query.lower()

        # Remove chars between specific spans
        query = re.sub("[\<\[].*?[\+\>]", "", query)
        
        # Remove the following characters
        punctuations = '''!()-[]{};:"\,<>./?@#$%^&*_~+'''
        
        query_clean = ""
        for char in query:
        
            if char not in punctuations:
                query_clean = query_clean + char
            
        # Remove white spaces
        query_clean = " ".join(query_clean.split())

        return query_clean

    # This function tokenizes all queries using the BERT tokenizer
    def GetEmbeddings(self, query):

        print(query)
        
        query_clean = self.CleanQueries(query)
        query_clean = query

        # Use the pre-loaded SBERT model to get the embeddings (512-dim)
        query_embedding = self.embedding_model.encode([query_clean])

        return query_embedding


    # This function tokenizes all queries using the BERT tokenizer
    def TokenizeQuery(self, query):
        
        query = "[CLS] " + query + " [SEP]"
        
        tokenized_query = [self.tokenizer.tokenize(query)]

        # Use BERT Tokenizer to convert subword tokens into indexes
        tokenized_query = [self.tokenizer.convert_tokens_to_ids(subwords) for subwords in tokenized_query]

        # Pad input tokens
        MAX_LEN = self.args.max_len
        tokenized_query = pad_sequences(tokenized_query, maxlen=MAX_LEN, dtype="long", truncating="post", padding="post")
        
        return tokenized_query


    # Main class is called in a new thread by UpdateInputQueue()
    def Main(self, transcript):

        tokenized_query = self.TokenizeQuery(transcript['sentence'])
        #embedding_query = self.GetEmbeddings(transcript['sentence'])

        #self.model_instance.Inference(tokenized_query)



    # This function updates the input que by emptying the transcription buffer
    def UpdateInputQueue(self, transcription_buffer):

        if len(transcription_buffer) > 0:

            for transcript in transcription_buffer:
                main = Thread(target = self.Main(transcript) )
                main.start()

            # Clear the transcription buffer
            transcription_buffer = list()
            
        return transcription_buffer


    # Only for test purposes
    def GetItems(self):

        print(self.input_queue.empty())
        for i in range(self.input_queue.qsize()):
            print(self.input_queue.get())










        

