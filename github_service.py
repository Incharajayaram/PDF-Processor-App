import requests
import json
import logging
import time
from typing import Dict, List, Optional
from time import sleep

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self, token=None):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
    
    def get_organization_info(self, company_name: str) -> Optional[Dict]:
        """search for organization by name and get details"""
        try:
            #first, search for the organization
            org_username = self._search_organization(company_name)
            
            if not org_username:
                logger.warning(f"No GitHub organization found for company: {company_name}")
                return None
            
            #get organization details
            url = f"{self.base_url}/orgs/{org_username}"
            response = self._make_request(url)
            
            if response and response.status_code == 200:
                org_data = response.json()
                return {
                    'login': org_data.get('login'),
                    'name': org_data.get('name'),
                    'description': org_data.get('description'),
                    'blog': org_data.get('blog'),
                    'location': org_data.get('location'),
                    'email': org_data.get('email'),
                    'public_repos': org_data.get('public_repos'),
                    'followers': org_data.get('followers'),
                    'created_at': org_data.get('created_at'),
                    'updated_at': org_data.get('updated_at'),
                    'type': org_data.get('type'),
                    'html_url': org_data.get('html_url')
                }
            elif response and response.status_code == 404:
                #try as user instead of org
                return self._get_user_info(org_username)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching organization info: {str(e)}")
            return None
    
    def _search_organization(self, company_name: str) -> Optional[str]:
        """search for github organization by company name"""
        try:
            #clean up company name for search
            search_query = company_name.lower().replace(' ', '').replace(',', '').replace('.', '')
            
            #common mappings for tech companies
            company_mappings = {
                'google': 'google',
                'microsoft': 'microsoft',
                'facebook': 'facebook',
                'meta': 'facebook',
                'amazon': 'amzn',
                'apple': 'apple',
                'netflix': 'netflix',
                'uber': 'uber',
                'airbnb': 'airbnb',
                'spotify': 'spotify',
                'twitter': 'twitter',
                'x': 'twitter',
                'tesla': 'tesla',
                'oracle': 'oracle',
                'ibm': 'ibm',
                'intel': 'intel',
                'nvidia': 'nvidia',
                'adobe': 'adobe',
                'salesforce': 'salesforce',
                'paypal': 'paypal',
                'stripe': 'stripe',
                'square': 'square',
                'shopify': 'shopify',
                'twilio': 'twilio',
                'atlassian': 'atlassian',
                'slack': 'slackhq',
                'docker': 'docker',
                'kubernetes': 'kubernetes',
                'hashicorp': 'hashicorp',
                'elastic': 'elastic',
                'mongodb': 'mongodb',
                'redis': 'redis',
                'postgresql': 'postgresql',
                'apache': 'apache',
                'mozilla': 'mozilla',
                'wordpress': 'wordpress',
                'automattic': 'automattic'
            }
            
            #check if we have a direct mapping
            if search_query in company_mappings:
                return company_mappings[search_query]
            
            #search using github search api
            search_url = f"{self.base_url}/search/users"
            params = {
                'q': f"{company_name} type:org",
                'per_page': 5
            }
            
            response = self._make_request(search_url, params=params)
            
            if response and response.status_code == 200:
                results = response.json()
                if results.get('total_count', 0) > 0:
                    #return the first result's login
                    return results['items'][0]['login']
            
            #try exact match
            test_url = f"{self.base_url}/orgs/{search_query}"
            test_response = self._make_request(test_url)
            if test_response and test_response.status_code == 200:
                return search_query
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching for organization: {str(e)}")
            return None
    
    def _get_user_info(self, username: str) -> Optional[Dict]:
        """get user details if not an organization"""
        try:
            url = f"{self.base_url}/users/{username}"
            response = self._make_request(url)
            
            if response and response.status_code == 200:
                user_data = response.json()
                return {
                    'login': user_data.get('login'),
                    'name': user_data.get('name'),
                    'description': user_data.get('bio'),
                    'blog': user_data.get('blog'),
                    'location': user_data.get('location'),
                    'email': user_data.get('email'),
                    'public_repos': user_data.get('public_repos'),
                    'followers': user_data.get('followers'),
                    'created_at': user_data.get('created_at'),
                    'updated_at': user_data.get('updated_at'),
                    'type': user_data.get('type'),
                    'html_url': user_data.get('html_url'),
                    'company': user_data.get('company')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching user info: {str(e)}")
            return None
    
    def get_organization_members(self, company_name: str, limit: int = 100) -> List[Dict]:
        """get public members of an organization"""
        try:
            #first get the organization username
            org_username = self._search_organization(company_name)
            if not org_username:
                logger.warning(f"No GitHub organization found for company: {company_name}")
                return []
            
            members = []
            page = 1
            per_page = 30
            
            while len(members) < limit:
                url = f"{self.base_url}/orgs/{org_username}/members"
                params = {'page': page, 'per_page': per_page}
                
                response = self._make_request(url, params=params)
                
                if response and response.status_code == 200:
                    page_members = response.json()
                    if not page_members:
                        break
                    
                    for member in page_members:
                        members.append({
                            'login': member.get('login'),
                            'avatar_url': member.get('avatar_url'),
                            'html_url': member.get('html_url'),
                            'type': member.get('type')
                        })
                    
                    if len(page_members) < per_page:
                        break
                    
                    page += 1
                elif response and response.status_code == 404:
                    #if org not found, return empty list
                    logger.warning(f"Organization {org_username} not found")
                    break
                else:
                    break
            
            return members[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching organization members: {str(e)}")
            return []
    
    def _make_request(self, url: str, params: Dict = {}, retry_count: int = 3) -> Optional[requests.Response]:
        """make http request with rate limit handling"""
        for attempt in range(retry_count):
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                
                #check rate limit
                if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers:
                    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                    if remaining == 0:
                        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                        sleep_time = max(reset_time - int(time.time()), 1)
                        logger.warning(f"Rate limit exceeded. Sleeping for {sleep_time} seconds")
                        sleep(sleep_time)
                        continue
                
                return response
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error (attempt {attempt + 1}/{retry_count}): {str(e)}")
                if attempt < retry_count - 1:
                    sleep(2 ** attempt)  #exponential backoff
                
        return None