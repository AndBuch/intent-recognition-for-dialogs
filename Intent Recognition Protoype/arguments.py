import os

class Arguments(object):

    def __init__(self):
        
        # These are basic paths for data handling
        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        self.pretrained_model = self.dir_path + '/model' + '/model_pretrained.pth.tar'
        self.labels_path = self.dir_path + '/model' + '/speechact_dictionary.json'
        
        # These define the model type and how many tokens a search query can have
        self.model_type = 'bert-base-multilingual-uncased'
        self.max_len = 256

        # This needed for the model in model.py and specifies how many labels are to be predicted
        self.num_intent_labels = 8







