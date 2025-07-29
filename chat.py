# This script is uesd to convert the data from client to the Gemini format.
import http.client
import requests
import json
from dotenv import load_dotenv
import os
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
base_url = os.getenv("BASE_URL") or "https://generativelanguage.googleapis.com/"
safetySettings_threhold = "BLOCK_NONE" # Set the safety settings threshold for the Google GenAI API
safetySettings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT", "threshold": safetySettings_threhold
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": safetySettings_threhold
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": safetySettings_threhold
    },
    {
        "category" : "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold" : safetySettings_threhold
    },
    {
        "category" : "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold" : safetySettings_threhold
    }
]
def send_request(gemini_request,model):
    google_gemini_url = base_url + "v1beta/models/" + model + ":generateContent"
    chat_header = {
        "x-goog-api-key" : gemini_api_key,
        "Content-Type" : "application/json"
    }
    response = requests.post(google_gemini_url, headers=chat_header, data=gemini_request)
    return response.json(), response.status_code
def getModel():
    req_url = base_url + "v1beta/models" + "?key=" + gemini_api_key
    response = requests.get(req_url)
    status_code = response.status_code
    return response.json()
if __name__ == "__main__":
    print("You can't run this script directly. Run main.py instead.")