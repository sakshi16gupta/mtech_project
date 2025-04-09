import importlib
import json
import yaml
import os
from yaml.loader import SafeLoader
from dataclasses import dataclass
import pandas as pd

@dataclass
class FeedbackResponse:
    
    message: str = ""
    query_id: str = ""                     
    error_code: int = 0 
    error_msg: str = "Success"

    def feedback_response(self):
        return json.dumps( 
            {
                "fdk_response": { 
                    "query_id": self.query_id, 
                    "message": self.message,
                    },
                "error": {
                    "error_code": self.error_code,
                    "error_message": self.error_msg
                    }
            }
    ) 

class TenantFeedbackClass:
    def __init__(self):
        pass
    def tenant_run(self,filename,request_data):
        # Reading the feedback data file from CDL
        # Reading all CSV files in the directory and merging them into a single DataFrame
        feedback_data = pd.read_csv(filename)

        #Updating the CDL data according to query_id
        feedback_data.loc[feedback_data["Query_ID"] == request_data["query_id"], ["Feedback","Rating"]] = \
                request_data["feedback"]["description"],request_data["feedback"]["rating"]
        feedback_data.to_csv(filename, index=False)

def run_feedback(review_data):
    res = FeedbackResponse()
    request_data = dict()

    try:
        # Response data extraction
        request_data = json.loads(review_data)["fdk_request"]

        # Generating dynamic path
        query_date = str(request_data["query_id"]).split("-")[-1]
        file_directory = "./prediction_"+query_date + '.csv'
        # tenant specific invoke of run function
        tenant = TenantFeedbackClass()
        tenant.tenant_run(file_directory, request_data)

        # assigning values to response object
        res.message = "Thanks you for your feedback"
        res.query_id = request_data["query_id"]
        return res.feedback_response()

    except Exception as error:
        # General Exception handling for error message capturing
        res.query_id = request_data["query_id"]
        res.message = str(error)
        res.error_code = 500
        res.error_msg = "Python Error"
        return res.feedback_response()