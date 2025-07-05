import os
import json
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, api_key=None):
        self.api_key = api_key
        
    def extract_company_name(self, text: str) -> Optional[str]:
        """extract tech company name from text using free LLM APIs"""
        #first try with google gemini (free tier)
        result = self._extract_with_gemini(text)
        if result:
            return result
            
        #fallback to hugging face free models
        result = self._extract_with_huggingface_free(text)
        if result:
            return result
            
        #final fallback to pattern matching
        return self._fallback_extraction(text)
    
    def _extract_with_gemini(self, text: str) -> Optional[str]:
        """use google gemini free api for extraction"""
        try:
            #using gemini via google ai studio free tier
            if not self.api_key:
                logger.info("No Gemini API key provided, skipping Gemini")
                return None
                
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
            
            prompt = (
                "Extract the name of any prominent tech company mentioned in this text. "
                "Return only the company name, nothing else. "
                "If no tech company is found, return 'none'.\n\n"
                f"Text: {text[:2000]}"
            )
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 50
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{url}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    extracted = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    return extracted if extracted.lower() != 'none' else None
            
            return None
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return None
    
    def _extract_with_huggingface_free(self, text: str) -> Optional[str]:
        """use hugging face free inference api"""
        try:
            #using free hugging face inference api (no auth required for some models)
            API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"
            
            prompt = (
                "Extract the name of the prominent tech company mentioned in this text. "
                "Return only the company name. Text: " + text[:1000]
            )
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": 50,
                    "temperature": 0.1
                }
            }
            
            response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    extracted = result[0].get('generated_text', '').strip()
                    return extracted if extracted and extracted.lower() != 'none' else None
                elif isinstance(result, str):
                    return result.strip() if result.strip() else None
            
            return None
            
        except Exception as e:
            logger.error(f"Hugging Face free API error: {str(e)}")
            return None
    
    
    def _fallback_extraction(self, text: str) -> Optional[str]:
        """fallback extraction using pattern matching"""
        import re
        
        #common tech company patterns
        tech_companies = {
            'microsoft': 'microsoft',
            'google': 'google',
            'facebook': 'facebook',
            'meta': 'facebook',
            'amazon': 'amazon',
            'aws': 'aws',
            'apple': 'apple',
            'netflix': 'netflix',
            'uber': 'uber',
            'airbnb': 'airbnb',
            'spotify': 'spotify',
            'twitter': 'twitter',
            'tesla': 'tesla',
            'oracle': 'oracle',
            'ibm': 'ibm',
            'intel': 'intel',
            'nvidia': 'nvidia',
            'adobe': 'adobe',
            'salesforce': 'salesforce',
            'paypal': 'paypal',
            'stripe': 'stripe',
            'github': 'github',
            'gitlab': 'gitlab',
            'docker': 'docker',
            'kubernetes': 'kubernetes',
            'tensorflow': 'tensorflow',
            'pytorch': 'pytorch',
            'react': 'facebook',
            'angular': 'angular',
            'vue': 'vuejs'
        }
        
        text_lower = text.lower()
        for company, github_name in tech_companies.items():
            if company in text_lower:
                logger.info(f"Found company '{company}' mapped to GitHub org '{github_name}'")
                return github_name
        
        #try to find github urls
        github_pattern = r'github\.com/([a-zA-Z0-9-]+)'
        matches = re.findall(github_pattern, text)
        if matches:
            return matches[0]
        
        return None