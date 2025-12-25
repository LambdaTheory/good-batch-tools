import requests
import json
import time

class AlipayAPI:
    def __init__(self):
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "origin": "https://b.alipay.com",
            "referer": "https://b.alipay.com/",
        }
        self.cookie = ""
        self.ctoken = ""
    
    def extract_ctoken(self, cookie):
        """Extracts ctoken from cookie string."""
        if not cookie:
            return ""
        try:
            # Look for ctoken=...; or ctoken=... at end of string
            import re
            match = re.search(r'ctoken=([^;]+)', cookie)
            if match:
                return match.group(1)
        except:
            pass
        return ""

    def update_config(self, cookie, ctoken=None):
        # Clean cookie: remove newlines and leading/trailing whitespace
        if cookie:
            # 1. Strip whitespace
            cookie = cookie.strip().replace('\n', '').replace('\r', '')
            # 2. Remove non-ASCII characters (headers must be Latin-1/ASCII)
            # This handles cases where user pastes text containing Chinese or other artifacts
            try:
                cookie.encode('latin-1')
            except UnicodeEncodeError:
                # Filter out non-ASCII characters
                cookie = ''.join(c for c in cookie if ord(c) < 256)
            
        self.cookie = cookie
        if ctoken:
            self.ctoken = ctoken
        else:
            self.ctoken = self.extract_ctoken(cookie)
        self.headers['cookie'] = cookie
        # Sometimes ctoken is also in headers or query params
        
    def upload_image(self, file_obj):
        """
        Uploads an image to Alipay Material Center.
        Endpoint: https://materialcenter.alipay.com/material/uploadImageV2.json?operateFrom=B_ALIPAY
        """
        url = "https://materialcenter.alipay.com/material/uploadImageV2.json"
        params = {
            "operateFrom": "B_ALIPAY"
        }
        
        # Additional form fields based on upload-pic.md
        data = {
            "fileName": file_obj.filename,
            "source": "materialCenter",
            "operateFrom": "B_ALIPAY",
            "directoryId": "0",
            "ownerId": ""
        }
        
        # Construct files payload
        # file_obj is a Werkzeug FileStorage object
        files = {
            'file': (file_obj.filename, file_obj.stream, file_obj.mimetype)
        }
        
        # Based on upload-pic.md, it's a POST request
        try:
            response = requests.post(url, headers=self.headers, params=params, data=data, files=files, verify=False)
            response.raise_for_status()
            data = response.json()
            
            if data.get('success'):
                return {
                    "status": "success",
                    "url": data['data']['link'],
                    "fileId": data['data']['fileId'],
                    "imageId": data['data']['imageId']
                }
            else:
                return {"status": "error", "message": str(data)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def create_good(self, item_data):
        """
        Creates a good.
        Endpoint: https://appxprod.alipay.com/operation/item/normal/create.json
        """
        url = "https://appxprod.alipay.com/operation/item/normal/create.json"
        params = {
            "ctoken": self.ctoken,
            "pamir_app_scene": "MRCH",
            "appId": item_data.get('appId', '2021005181665859') # Default or from data
        }
        
        # Construct the payload based on creat-good.md
        # The user's provided payload is complex. We need to construct it dynamically based on the Excel data.
        # For now, we will assume item_data contains the necessary fields or the full payload structure.
        
        # Important: The payload in the MD file shows a specific structure.
        # We need to ensure headers include content-type: application/json
        
        headers = self.headers.copy()
        # requests will set the correct Content-Type when using the json parameter
        
        try:
            response = requests.post(url, headers=headers, params=params, json=item_data, verify=False)
            # Response handling
            if response.status_code == 200:
                return {"status": "success", "response": response.json()}
            else:
                return {"status": "error", "code": response.status_code, "text": response.text}
        except Exception as e:
            return {"status": "error", "message": str(e)}
