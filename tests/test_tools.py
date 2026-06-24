import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_agents.tools.read_telemetry import read_telemetry
from fleet_agents.tools.calculate_rul import calculate_rul
from fleet_agents.tools.check_baselines import check_baselines
from fleet_agents.tools.submit_ticket import submit_ticket

class TestFleetTools(unittest.TestCase):
    
    def test_read_telemetry_valid(self):
        # Ingest cycle 38
        res = read_telemetry(38)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["Engine_ID"], "TF-804")
        self.assertEqual(res["Cycle"], 38)
        self.assertIn("T24_LPC_Outlet_Temp", res)
        
    def test_read_telemetry_invalid(self):
        res = read_telemetry(999)
        self.assertEqual(res["status"], "error")
        
    def test_calculate_rul(self):
        # Call calculate_rul with typical cycle 38 inputs
        res = calculate_rul(
            setting_1=-0.0007,
            setting_2=-0.0004,
            setting_3=100.0,
            sensor_2=642.5,
            sensor_11=47.5,
            sensor_9=9030.0,
            sensor_8=2388.1,
            sensor_15=8.42
        )
        self.assertEqual(res["status"], "success")
        self.assertIsInstance(res["estimated_rul"], int)
        self.assertTrue(0 <= res["estimated_rul"] <= 200)
        
    def test_check_baselines_normal(self):
        # Sensor values well within limits
        res = check_baselines(
            t24=641.9,
            p30=47.3,
            nf=9040.0,
            nc=2388.0,
            bpr=8.42
        )
        self.assertEqual(res["status"], "success")
        self.assertFalse(res["is_anomalous"])
        self.assertEqual(len(res["failing_sensors"]), 0)
        
    def test_check_baselines_anomalous(self):
        # T24 high anomaly (UCL is 643.0)
        res = check_baselines(
            t24=645.0,
            p30=47.3,
            nf=9040.0,
            nc=2388.0,
            bpr=8.42
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["is_anomalous"])
        self.assertIn("T24_LPC_Outlet_Temp", res["failing_sensors"])
        
    @patch('requests.post')
    def test_submit_ticket(self, mock_post):
        # Mock API response for successful ticket creation
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "ticket_id": "MNT-12345",
            "engine_id": "TF-804",
            "failing_sensors": ["T24_LPC_Outlet_Temp"],
            "estimated_rul": 25,
            "priority_level": "HIGH",
            "status": "OPEN",
            "created_at": "2026-06-24T14:16:23"
        }
        mock_post.return_value = mock_response
        
        # Clear active tickets if any for testing
        active_tickets_file = 'data/active_tickets.json'
        if os.path.exists(active_tickets_file):
            try:
                os.remove(active_tickets_file)
            except Exception:
                pass
                
        res = submit_ticket(
            engine_id="TF-804",
            failing_sensors=["T24_LPC_Outlet_Temp"],
            estimated_rul=25,
            priority_level="HIGH"
        )
        
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["ticket_id"], "MNT-12345")
        
        # Test duplicate prevention (should return skipped)
        res_duplicate = submit_ticket(
            engine_id="TF-804",
            failing_sensors=["T24_LPC_Outlet_Temp"],
            estimated_rul=25,
            priority_level="HIGH"
        )
        self.assertEqual(res_duplicate["status"], "skipped")
        self.assertEqual(res_duplicate["ticket_id"], "MNT-12345")

if __name__ == '__main__':
    unittest.main()
