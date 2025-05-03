import requests
import json
import os
from dotenv import load_dotenv
from config import settings

load_dotenv()

class AIService:
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(self, messages):
        payload = {
            "model": "qwen/qwen2.5-vl-32b-instruct",
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 1000
        }
        
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"AI request failed: {response.text}")