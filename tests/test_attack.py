import unittest
import subprocess
import os
import sys

class AttackSimulatorTest(unittest.TestCase):
    def test_simulator_execution(self):
        """Test that the attack simulator runs without crashing."""
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'attack_simulator.py')
        
        # We run it against localhost. Since there's no SSH server running on localhost by default 
        # in the CI runner, it will just fail to connect, which is handled gracefully by the script.
        result = subprocess.run(
            [sys.executable, script_path, "--target", "127.0.0.1", "--count", "2"],
            capture_output=True, text=True
        )
        
        # Verify the script completes successfully and outputs the completion message
        self.assertEqual(result.returncode, 0)
        self.assertIn("Simulation complete", result.stdout)
        
if __name__ == '__main__':
    unittest.main()
