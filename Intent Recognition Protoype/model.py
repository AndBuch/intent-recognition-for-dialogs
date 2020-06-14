# Import model specific libraries
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn import BCEWithLogitsLoss
from pytorch_pretrained_bert import BertTokenizer, BertConfig
from pytorch_pretrained_bert import BertAdam, BertForSequenceClassification, BertModel
from transformers import AutoModel, AutoTokenizer

# Data handling
import numpy as np
import pandas as pd


# This class defines the model architecture. It will only be instantiated and then the weights are loaded! 
class GermanBertMultiClassificationMultilingual(BertModel):
    
    def __init__(self, config, args):
        super(GermanBertMultiClassificationMultilingual, self).__init__(config)
        
        self.num_labels = args.num_intent_labels
        self.bert = BertModel(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.linear = nn.Linear(config.hidden_size, args.num_intent_labels)
        self.apply(self.init_bert_weights)
        
        
    def forward(self, input_ids, token_type_ids = None, attention_masks = None, labels = None, validation = None):
        _, pooled_output = self.bert(input_ids, attention_masks, token_type_ids)
        pooled_output = self.dropout(pooled_output)
        logits = self.linear(pooled_output)
        
        if labels is not None:
            
            # In case of Binary Classification use argmax to retrieve highest 
            if self.num_labels == 2:
                loss_fct = nn.CrossEntropyLoss()
                loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))
            
            else:
                loss_fct = nn.CrossEntropyLoss()
                loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))
                
            return loss
        
        else:
            return logits


class Model(object):


    def __init__(self, args):
        
        # Save the arguments class
        self.args = args

        # Import speech-act dictionary from the json-file
        self.label_dict = pd.read_json(self.args.labels_path, lines=True)

        # Load GPU if available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        if str(self.device) == "cuda":
            torch.cuda.get_device_name(0)
            print("Device is GPU...")

        else:
            print("Device is CPU...")

        # Instantiate the basic structure of the model
        #self.model = GermanBertMultiClassificationMultilingual.from_pretrained(self.args.model_type , self.args)
        #self.model.to(self.device)

        # Now, load the pretrained weigths into the model
        checkpoint = torch.load(self.args.pretrained_model, map_location=torch.device(self.device))
        self.model = checkpoint['model']

        print("Model has been initialized with the pretrained weights...")


    def Inference(self, tokenized_query):

        # Convert tokenized query to tensor
        tokenized_query_tensor = torch.tensor(tokenized_query)
        tokenized_query_tensor = tokenized_query_tensor.to(self.device)

        # Now, set the model into evluation mode
        self.model.eval()

        # Let's begin the inference calls
        with torch.no_grad():
            outputs = self.model(tokenized_query_tensor, token_type_ids = None, attention_masks = None, labels = None)

         # Move logits and labels to CPU
        intent_logits = outputs.detach().cpu().numpy()    
        
        # Get intent predictions
        print(intent_logits)
        intent_pred_flat = np.argmax(intent_logits, axis=1).flatten()
        intent_type = self.label_dict['speech_act'][intent_pred_flat]

        # Print the  result
        print("Detected intent is %s" %intent_type)

    



    





    


    

