import json
from typing import Any
from dataclasses import dataclass,field
import pandas as pd
from datetime import datetime
import uuid
import os
import joblib
from autocorrect import Speller
import regex as re
from sentence_transformers import SentenceTransformer
from sentence_transformers import util
import torch
import time
import nltk
nltk.download('averaged_perceptron_tagger_eng')
nltk.download('punkt_tab')

# data class for response object of search endpoint
@dataclass
class SearchResponse:
    
    data: list = field(default_factory=list)
    query_id: str = "" 
    response: list = field(default_factory=list)
    error_code: int = 0
    error_msg: str = "Success"

    def search_response(self) -> Any:
        return json.dumps( 
            { 
                "fdk_response": { 
                    "query_id": self.query_id, 
                    "query": self.data, 
                    "result": self.response
                }, 
                "error": {
                    "error_code": self.error_code, 
                    "error_message": self.error_msg
                }
            }
    )

# This is the dataclass for the recommendations generated by the algorithm
@dataclass
class PredictionData:
    query_id: Any
    query: Any
    response: Any
    feedback: str = ""
    rating: str = ""
    timestamp: datetime = datetime.now().strftime('%Y%m%d-%H:%M:%S')

    def record_dictionary(self):
        return { "Query_ID": [self.query_id],
        "Timestamp": [self.timestamp],
        "Query": [self.query],
        "Response": [self.response],
        "Feedback": [self.feedback],
        "Rating": [self.rating],
        }

        # return "\n"+str(self.query_id)+","+str(self.timestamp)+","+str(self.query)+","+str(self.response)+","+str(self.feedback)+","+str(self.rating)

def read_prediction_files(prediction_folder):
    feedbacks = []
    paths = os.listdir(prediction_folder)
    for filename in paths:
        print("Reading file: ", filename)
        feedbacks.append(pd.read_csv(prediction_folder+filename))
        print(feedbacks)
    predicted_data = pd.concat(feedbacks)[['Query','Feedback']].dropna().reset_index(drop=True)
    #featurisation on predicted data
    remove_words = "feedback|result|response|computer|not|resolved|test"
    predicted_data_copy = predicted_data.copy()
    for ind,feedback in zip(predicted_data_copy.index,predicted_data_copy["Feedback"]):
        if re.findall(remove_words, feedback.lower()) or len(feedback.split(" ")) < 3:
            predicted_data = predicted_data.drop(ind)
    for ind in predicted_data.index:
        predicted_data['Query'][ind] = predicted_data['Query'][ind][2:-2]
    return predicted_data

def result_prediction_file(model,feedback_data,query):
    # feedback query searching
    results1 = []
    for f in feedback_data["Query"]:
        print(repr(f))
    top_k = 5
    if top_k > len(feedback_data):
        top_k = len(feedback_data)

    #Sentences are encoded by calling model.encode()
    query_embeddings = model.encode(query,convert_to_tensor=True)
    embeddings = model.encode(list(feedback_data["Query"]),convert_to_tensor=True)

    # We use cosine-similarity and torch.topk to find the highest 5 scores
    cos_scores = util.cos_sim(query_embeddings, embeddings)[0]
    print(cos_scores)
    top_results = torch.topk(cos_scores, k=top_k)

    for score, idx in zip(top_results[0], top_results[1]):
        results1.append([list(feedback_data["Query"])[idx],list(feedback_data["Feedback"])[idx],round(score.item(),2)])

    # final results
    feedback_results = pd.DataFrame(columns=["Response","Scores"])
    for res in results1:
        if res[2] >= 0.95:
            feedback_results.loc[len(feedback_results.index)] = [res[1], res[2]]
        else:
            break
    return feedback_results

class TenantSearchClass:
    def __init__(self):
        """
        Loading Model, Embedded corpus & Issues data into global variable
        Model -->> Symmetric and Asymetric Semantic search model
        Issue Data -->> Preprocessed Dataset
        Embedded Corpus -->> Encoded short description and cause object data for runtime comparision
        """
        self.top_k: int
        self.short_description_embedded_corpus: Any
        self.cause_object_embedded_corpus: Any
        self.issue_data: Any
        self.symmetric_model: Any
        self.asymmetric_model: Any
        self.CDL_DIRECTORY_FILE = "/Prediction/US3/prediction_"
        self.CDL_PREDICTION_FOLDER = "/Prediction/US3"
        self.spell: Any

        model_path="../ModelTraining"

        # Loading Issue data
        issue_data_path = "../Preprocessed/processed_dataset.csv"
        self.issue_data = pd.read_csv(issue_data_path)

        # Loading Symmetric Semantic Search Model
        symmetric_model_path = model_path + "/symmetric_model.pkl"
        self.symmetric_model = joblib.load(symmetric_model_path)

        # Loading Asymmetric Semantic Search Model
        # Quickfix validation for Gen2 migration 
        # asymmetric_model_path = model_path + "/" + str(cfg["asymmetric_search_model_name"])
        # self.asymmetric_model = joblib.load(asymmetric_model_path)
        self.asymmetric_model = SentenceTransformer('sentence-transformers/msmarco-distilbert-base-v4')

        # Loading Short Descripiton Embedded corpus
        short_description_corpus_path = model_path + "/short_description_corpus_data.pkl"
        self.short_description_embedded_corpus = joblib.load(short_description_corpus_path)

        # Loading Cause Object Embedded corpus
        cause_object_corpus_path = model_path + "/cause_object_corpus_data.pkl"
        self.cause_object_embedded_corpus = joblib.load(cause_object_corpus_path)

        # Spelling correction
        self.spell = Speller(lang='en')

    def data_processing(self,data) -> Any:
        # Tokenize the query
        process_data = data
        tokens = [i for item in data for i in item.split()]

        # Joining the tokens
        context_dictionary = ['ls12','ls10','ls18','ls24','rtd','d11','d13','d14','v24','limit','ls9','v2','v7','chariot',
                            'ls15','v22','ls2','membrane','locking','rotation','d10','open','d17','precon','v6','ls8,',
                            'ls21','press','lock','opening','loading','d1bis','ls5','steam','ls27','v3','ls20','vinj',
                            'd02','d19','d06','d18','lid','raise','d09','valves','ls28','cylinder','d07','ls6','vter',
                            'v1','v4bis','d03','v9','hooks','release','unloading','ls16','v1bis','v4ebis','to','ls17',
                            'd19bis','close','jib','d04','hydraulic','ls1','d1ter','d20','ring','v23','sectors','d15',
                            'preconfirmation','hook','d01','closing','unlock','head','v34','ls7,','pin','ls19','lower',
                            'v19','d20bis','d12','fingers','d05','d3bis','switches','moldback', 'orifice', 'valve',
                            'kpot','reheat','dilate']
        p = re.compile(r"\L<words>", words=context_dictionary)
        for idx, val in enumerate(tokens):
            if not p.search(val.lower()):
                tokens[idx] = self.spell(tokens[idx].lower())
            process_data = [' '.join(tokens)]

        return process_data

    def symmetric_semantic_search(self,feature_name,query):

        # assigning dataframe,long description and feature into variables
        df_updated,solution = self.issue_data,"WO rem long desc"
        cfg = {"cause_object": "Cause object",
            "short_description": "WO Description",
            "long_description": "WO rem long desc"}
        feature = cfg[feature_name]

        # creating corpus of unique feature values
        corpus = list(df_updated[feature].drop_duplicates())

        # defining top k with constant value
        top_k = 5

        # encoding query
        query_embeddings = self.symmetric_model.encode(query,convert_to_tensor=True)

        # Assigning embeddings and topk according to the feature
        if feature == "Cause object":
            embeddings = self.cause_object_embedded_corpus
            top_k = 2
        elif feature == "WO Description":
            embeddings = self.short_description_embedded_corpus
            top_k = 15

        # if corpus length is less that topk then changing its value
        if top_k > len(corpus):
            top_k = len(corpus)

        # calculation cosine scores using cosine similarity and
        # generating top results using torch.topk
        # between query and feature embeddings
        cos_scores = util.cos_sim(query_embeddings, embeddings)[0]
        top_results = torch.topk(cos_scores, k=top_k)

        #saving dataset rows which has top k feature in the dataframe
        filtered_feature = []
        i = 0
        for score, idx in zip(top_results[0], top_results[1]):
            filtered_feature.append(corpus[top_results[1][i]])
            i += 1
        df_feature = df_updated[df_updated[feature].isin(filtered_feature)]

        #nltk tokenization of the feature filtered dataframe
        corpus = []
        for index,row in df_feature.drop_duplicates(subset=solution,keep="first").iterrows():
            sen = row[solution]
            token = nltk.word_tokenize(sen)
            tagged_list = nltk.pos_tag(token)
            corpus.append([tagged_list,row[feature]])


        # extractong the solution which have verbs second form and
        # making two lists for solution and feature
        feature_corpus =[]
        feature_list = []
        for sen1 in corpus:
            for t in sen1[0]:
                if t[1] == "VBD" or t[1] == "VBN":
                    feature_corpus.append(" ".join([w[0] for w in sen1[0]]))
                    feature_list.append(sen1[1])
                    break
        return feature_corpus,feature_list

    def tenant_run(self,data,feedback_data):
        # Invoking data preprocessing function
        process_data = self.data_processing(data)

        # initialising output list
        outputlist = list()

        # Invoking symmetric semantic search with feature cause object if the lengthof corpus is less
        # then invoking symmetric semantic search with feature short description
        description_corpus,feature_list = self.symmetric_semantic_search("cause_object",process_data)

        if len(description_corpus) < 200:
            description_corpus,feature_list = self.symmetric_semantic_search("short_description",process_data)

        result2 = []

        # initialising value of topk for asymmetric semantic dearch on the
        # long description corpus which has been filtered out
        top_k = min(15, len(description_corpus))

        # encoding query and long description
        query_embedding = self.asymmetric_model.encode(process_data,convert_to_tensor=True)
        passage_embedding = self.asymmetric_model.encode(description_corpus,convert_to_tensor=True)

        # We use cosine-similarity and torch.topk to find the highest top_k scores
        cos_scores = util.cos_sim(query_embedding, passage_embedding)[0]
        top_results = torch.topk(cos_scores, k=top_k)

        # saving top_k results and scores in the list
        for score, idx in zip(top_results[0], top_results[1]):
            result2.append((description_corpus[idx],"{:.4f}".format(score)))

        # creating the dataframe for top_k results with three columns as response score and feature
        result_df = pd.DataFrame(result2,columns=["Response","Scores"])
        result_df["Cause object/Short Description"] = ""
        for i,res in enumerate(result_df["Response"]):
            result_df["Cause object/Short Description"][i] = (feature_list[description_corpus.index(res)])

        # extracting responses from top_k results
        response_corpus = result_df["Response"]

        # encoding top_k responses
        corpus_sentences = list(response_corpus)
        print("Encode the corpus. This might take a while")
        corpus_embeddings = self.symmetric_model.encode(corpus_sentences,show_progress_bar=True, convert_to_tensor=True)

        # clustering the top_k responses using FAST Clustering
        print("Start clustering")
        start_time = time.time()
        
        # clustering the tiop_k responses using FAST Clustering
        clusters = util.community_detection(corpus_embeddings, min_community_size=1, threshold=0.75)

        print("Clustering done after {:.2f} sec".format(time.time() - start_time))

        #extracting the nearest repsonse from each cluster
        df_final = pd.DataFrame()
        for i, cluster in enumerate(clusters):
            df_final = pd.concat([df_final,pd.DataFrame(result_df.iloc[cluster[0:]].sort_values(by="Scores",ascending=False))],ignore_index=True)
        #sorting the reponses according to the scores for final recommendations
        df_final = df_final.sort_values(by="Scores",ascending=False)

        # prediction result
        try:
            feedback_results = result_prediction_file(self.symmetric_model,feedback_data,process_data)
        except Exception as e:
            feedback_results = []
        # df_final results length
        df_len = 5 - len(feedback_results)

        #combining results
        if len(feedback_results) > 0 and len(feedback_results) < 5:
            combined_results = feedback_results.append(df_final[["Response","Scores"]][:df_len]).reset_index(drop=True)
        elif len(feedback_results) == 5:
            combined_results = feedback_results
        else:
            combined_results = df_final[["Response","Scores"]]

        return process_data,combined_results
def file_operation(process_data,outputlist):
    file_name = f"prediction_{datetime.now().strftime('%Y%m%d')}.csv"
    if not os.path.isfile(file_name):
        #--> Preparing columns list
        column_names = ['Query_ID', 'Timestamp', 'Query', 'Response', 'Feedback', 'Rating']
        pd.DataFrame(columns = column_names).to_csv(file_name,index=False)
        
    query_id = f"{uuid.uuid4()}-{datetime.now().strftime('%Y%m%d')}"

    # Preparing new prediction record
    new_record = PredictionData(query_id = query_id,query = process_data, response = outputlist, feedback = "" ,rating = "",timestamp=datetime.now().strftime('%Y%m%d-%H:%M:%S'))

    # Append the feedback to feedback data file
    old_df = pd.read_csv(file_name)
    new_df = pd.DataFrame(new_record.record_dictionary())
    updated_df = pd.concat([old_df, new_df], ignore_index=True)
    updated_df.to_csv(file_name, index=False)

    return new_record.query_id

import traceback

def run_search(raw_data):
    print("###########################")
    print(os.path.abspath(os.curdir))
    # Search Response Object
    res = SearchResponse()
    try:
        # initialising output list
        outputlist = list()
        
        # Data extraction
        res.data = json.loads(raw_data)['data']

        # Invoking run function of tenant specific object
        feedback_data = read_prediction_files("./feedback/")
        print("Feedback data:", feedback_data)
        tenant = TenantSearchClass()
        process_data, combined_results = tenant.tenant_run(res.data,feedback_data)

        # output list as final recommendations
        n = 1
        for ind in combined_results.index:
            if n == 4:
                break
            description = combined_results["Response"][ind]
            match_row = {
                        'rank': n,
                        'description': description,
                        'score': combined_results["Scores"][ind]
                        }
            outputlist.append(match_row)
            n += 1

        res.response = outputlist

        # Recoding the response data into CDL
        res.query_id = file_operation(process_data, res.response)

        # Logging for future troubleshooting
        print(json.dumps({ "input": process_data, "output": res.response }))

        return res.search_response()

    except Exception as error:
        # General Exception handling for error message capturing
        res.error_code = 500
        res.error_msg = str(error)
        print("Error occurred:", traceback.format_exc())
        return res.search_response()
    
