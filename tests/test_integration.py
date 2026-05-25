import unittest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

class TestIntegrationTests(unittest.TestCase):
    
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    def test_create_request_success(self):
        response = self.client.post('/api/create-request', 
            json={'weight': 5000, 'pickup': 'Москва', 'delivery': 'СПб', 'force_error': False})
        self.assertEqual(response.status_code, 200)
    
    def test_get_requests_returns_list(self):
        response = self.client.get('/api/requests')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()