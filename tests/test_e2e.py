import unittest
import requests
import threading
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

class TestE2ETests(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.server_thread = threading.Thread(target=lambda: app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False))
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(2)
    
    def test_full_scenario_success(self):
        response = requests.post('http://localhost:5001/api/create-request', 
            json={'weight': 5000, 'pickup': 'Москва', 'delivery': 'СПб', 'force_error': False})
        self.assertEqual(response.status_code, 200)
        print("✅ E2E тест пройден")

if __name__ == '__main__':
    unittest.main()