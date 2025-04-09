import urllib3
import json
from typing import Dict, Optional


class ClickUpClient:
    BASE_URL = "https://api.clickup.com/api/v2"
    
    def __init__(self, api_token: str):
        """Initialize ClickUp client with API token.
        
        Args:
            api_token (str): Your ClickUp API personal token
        """
        self.api_token = api_token
        self.http = urllib3.PoolManager()
        
    def get_task_details(self, task_id: str) -> Optional[Dict]:
        """Fetch task details from ClickUp by task ID.
        
        Args:
            task_id (str): The ID of the task to retrieve
            
        Returns:
            Optional[Dict]: Task details as a dictionary or None if request fails
            
        Raises:
            urllib3.exceptions.HTTPError: If the HTTP request fails
            json.JSONDecodeError: If the response cannot be parsed as JSON
        """
        headers = {
            "Authorization": self.api_token,
            "Content-Type": "application/json"
        }
        
        try:
            response = self.http.request(
                "GET",
                f"{self.BASE_URL}/task/{task_id}",
                headers=headers
            )
            
            if response.status == 200:
                return json.loads(response.data.decode('utf-8'))
            else:
                print(f"Error: Request failed with status {response.status}")
                print(f"Response: {response.data.decode('utf-8')}")
                return None
                
        except urllib3.exceptions.HTTPError as e:
            print(f"HTTP Error occurred: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            return None 
