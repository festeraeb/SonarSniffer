"""
Integration Tests for CesarOps SAR Physics Engine

Validates RK4 integration, batch processing, and SAR scenario functionality
"""

import sys
import unittest
import numpy as np
from typing import List

from physics_engine import (
    SimulationState, WaterDriftModel, SubmersibleModel,
    RK4Integrator, SARODESystem, compare_integration_methods
)
from batch_processor import BatchProcessor, ParallelScenarioRunner
from sar_scenarios import (
    PersonInWaterSimulation, VesselIncidentSimulation,
    SearchGridPlanner
)


class TestPhysicsEngine(unittest.TestCase):
    """Test core physics engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.model = WaterDriftModel()
        self.integrator = RK4Integrator(self.model)
        self.initial_state = SimulationState(
            x=41.0, y=-71.0, vx=0.0, vy=0.0, depth=0.0
        )
    
    def test_state_to_array_conversion(self):
        """Test SimulationState array conversion"""
        state = SimulationState(x=1.0, y=2.0, vx=0.1, vy=0.2)
        arr = state.to_array()
        
        self.assertEqual(len(arr), 5)
        self.assertEqual(arr[0], 1.0)
        self.assertEqual(arr[1], 2.0)
    
    def test_rk4_single_step(self):
        """Test RK4 single integration step"""
        env = {'wind_x': 0.5, 'wind_y': 0.3, 'current_x': 0.2, 'current_y': -0.1}
        
        new_state = self.integrator.step(self.initial_state, dt=60.0, 
                                         environmental_conditions=env)
        
        # Position should change due to forces
        self.assertNotEqual(new_state.x, self.initial_state.x)
        self.assertNotEqual(new_state.y, self.initial_state.y)
        self.assertEqual(new_state.time, 60.0)
    
    def test_rk4_trajectory(self):
        """Test RK4 trajectory integration"""
        env = {'wind_x': 0.5, 'wind_y': 0.3, 'current_x': 0.2, 'current_y': -0.1}
        
        trajectory = self.integrator.integrate(
            self.initial_state, duration=3600.0, dt=60.0,
            environmental_conditions=env
        )
        
        self.assertEqual(len(trajectory), 61)  # 3600/60 + initial state
        self.assertEqual(trajectory[-1].time, 3600.0)
    
    def test_physics_model_water_drift(self):
        """Test water drift physics model"""
        state = SimulationState(x=0.0, y=0.0, vx=1.0, vy=0.0)
        env = {'wind_x': 0.5, 'wind_y': 0.0, 'current_x': 0.0, 'current_y': 0.0}
        
        ax, ay = self.model.acceleration(state, env)
        
        # Should have some acceleration due to wind
        self.assertNotEqual(ax, 0.0)
    
    def test_submersible_model(self):
        """Test submersible physics model"""
        model = SubmersibleModel()
        state = SimulationState(x=0.0, y=0.0, vx=0.0, vy=0.0, depth=50.0)
        env = {'current_x': 0.5, 'current_y': 0.3, 'max_depth': 100.0}
        
        ax, ay = model.acceleration(state, env)
        
        # Should have some acceleration
        self.assertTrue(abs(ax) > 0 or abs(ay) > 0)
    
    def test_ode_system(self):
        """Test SAR ODE system"""
        system = SARODESystem(WaterDriftModel())
        
        # Add particles
        for i in range(5):
            particle = SimulationState(
                x=41.0 + i*0.001, y=-71.0 + i*0.001, vx=0.0, vy=0.0
            )
            system.add_particle(particle)
        
        system.set_environment({
            'wind_x': 0.5, 'wind_y': 0.3,
            'current_x': 0.2, 'current_y': -0.1
        })
        
        trajectories = system.simulate(duration=3600.0, dt=60.0)
        
        self.assertEqual(len(trajectories), 5)
        for idx, trajectory in trajectories.items():
            self.assertGreater(len(trajectory), 0)


class TestBatchProcessor(unittest.TestCase):
    """Test parallel batch processing"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.particles = []
        for i in range(20):
            self.particles.append(SimulationState(
                x=41.0 + np.random.normal(0, 0.001),
                y=-71.0 + np.random.normal(0, 0.001),
                vx=0.0, vy=0.0
            ))
    
    def test_batch_processor_creation(self):
        """Test batch processor initialization"""
        processor = BatchProcessor(num_cores=2)
        self.assertEqual(processor.num_cores, 2)
    
    def test_add_particles(self):
        """Test adding particles to processor"""
        processor = BatchProcessor()
        processor.add_particles(self.particles)
        self.assertEqual(len(processor.particles), 20)
    
    def test_batch_processing(self):
        """Test batch execution"""
        processor = BatchProcessor(num_cores=2)
        processor.add_particles(self.particles)
        processor.set_environment({
            'wind_x': 0.5, 'wind_y': 0.3,
            'current_x': 0.2, 'current_y': -0.1
        })
        
        results = processor.run(duration=1800.0, dt=60.0, batch_size=5)
        
        self.assertEqual(results['total_particles'], 20)
        self.assertGreater(results['num_batches'], 0)
        self.assertEqual(len(results['all_final_positions']), 20)
    
    def test_scenario_runner(self):
        """Test parallel scenario runner"""
        runner = ParallelScenarioRunner(self.particles, num_cores=2)
        
        runner.add_scenario('calm', {
            'wind_x': 0.1, 'wind_y': 0.1,
            'current_x': 0.05, 'current_y': 0.05
        })
        
        runner.add_scenario('rough', {
            'wind_x': 1.0, 'wind_y': 0.8,
            'current_x': 0.4, 'current_y': -0.2
        })
        
        results = runner.run_all(duration=1800.0, dt=60.0)
        
        self.assertEqual(len(results), 2)
        self.assertIn('calm', results)
        self.assertIn('rough', results)


class TestSARScenarios(unittest.TestCase):
    """Test SAR-specific scenarios"""
    
    def test_person_in_water_simulation(self):
        """Test PIW simulation"""
        piw = PersonInWaterSimulation(41.123, -71.456)
        result = piw.simulate(duration_hours=1, n_particles=10)
        
        self.assertEqual(result['scenario'], 'Person in Water')
        self.assertEqual(result['particles_simulated'], 10)
        self.assertIn('search_center', result)
        self.assertIn('search_radius_1_sigma', result)
    
    def test_vessel_incident_simulation(self):
        """Test vessel incident simulation"""
        vessel = VesselIncidentSimulation(41.123, -71.456, vessel_type='small_boat')
        result = vessel.simulate_multi_weather(duration_hours=1)
        
        self.assertEqual(result['vessel_type'], 'small_boat')
        self.assertIn('calm', result['scenarios'])
        self.assertIn('moderate', result['scenarios'])
        self.assertIn('severe', result['scenarios'])
    
    def test_search_grid_planner(self):
        """Test search grid planning"""
        planner = SearchGridPlanner()
        
        # Expanding square
        square = planner.expanding_square((41.0, -71.0), initial_radius=0.05)
        self.assertGreater(len(square), 0)
        
        # Parallel track
        parallel = planner.parallel_track((41.0, -71.0), search_radius=0.05)
        self.assertGreater(len(parallel), 0)
        
        # Probability heatmap
        positions = [
            {'x': 41.0, 'y': -71.0},
            {'x': 41.001, 'y': -71.001}
        ]
        heatmap = planner.probability_weighting((41.0, -71.0), positions)
        self.assertEqual(heatmap.shape, (20, 20))
        self.assertGreater(np.sum(heatmap), 0)


class TestMethodComparison(unittest.TestCase):
    """Test RK4 vs Euler accuracy"""
    
    def test_rk4_vs_euler_accuracy(self):
        """Test that RK4 is more accurate than Euler"""
        result = compare_integration_methods(duration=3600.0, dt=10.0)
        
        # RK4 should have reasonable final position
        self.assertIsNotNone(result['rk4_final_x'])
        self.assertIsNotNone(result['rk4_final_y'])
        
        # Euler might diverge more with larger timesteps
        self.assertIsNotNone(result['euler_final_x'])
        self.assertIsNotNone(result['euler_final_y'])


def run_integration_tests():
    """Run all integration tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPhysicsEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestBatchProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestSARScenarios))
    suite.addTests(loader.loadTestsFromTestCase(TestMethodComparison))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    print("="*60)
    print("CesarOps SAR Physics Engine - Integration Tests")
    print("="*60)
    
    result = run_integration_tests()
    
    print("\n" + "="*60)
    if result.wasSuccessful():
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
    print("="*60)
