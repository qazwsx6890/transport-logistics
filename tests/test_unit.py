import unittest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import retry, CircuitBreaker

class TestUnitTests(unittest.TestCase):
    
    def test_circuit_breaker_initial_state(self):
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=10)
        self.assertEqual(cb.state, 'CLOSED')
    
    def test_retry_decorator_success(self):
        mock_func = MagicMock(return_value="success")
        
        @retry(max_attempts=3, delay_seconds=0)
        def test_func():
            return mock_func()
        
        result = test_func()
        self.assertEqual(result, "success")

if __name__ == '__main__':
    unittest.main()