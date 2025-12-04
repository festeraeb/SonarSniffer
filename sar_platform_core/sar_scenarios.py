"""
SAR-Specific Simulation Scenarios for CesarOps

Pre-built simulation templates for common Search & Rescue scenarios:
- Person in water (PIW) drift prediction
- Debris field expansion
- Water rescue grid planning
- Search probability calculation
"""

import numpy as np
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass

from physics_engine import SimulationState, WaterDriftModel, SubmersibleModel
from batch_processor import BatchProcessor, ParallelScenarioRunner


@dataclass
class SARScenario:
    """Represents a SAR incident scenario"""
    name: str
    incident_type: str  # 'PIW', 'vessel', 'aircraft', 'hiker'
    initial_position: Tuple[float, float]  # (lat, lon)
    incident_time: str  # ISO format
    environmental_conditions: Dict[str, float]
    search_area_expansion: bool = True
    description: str = ""


class PersonInWaterSimulation:
    """
    Simulate person in water (PIW) drift prediction
    
    Used for search grid planning and probability calculations
    """
    
    def __init__(self, initial_lat: float, initial_lon: float):
        """
        Initialize PIW simulation
        
        Args:
            initial_lat: Incident latitude
            initial_lon: Incident longitude
        """
        self.initial_position = (initial_lat, initial_lon)
        self.dispersal_radius = 0.05  # degrees (~5km)
    
    def _create_scattered_particles(self, n_particles: int = 50) -> List[SimulationState]:
        """Create particle cloud representing uncertainty in initial position"""
        particles = []
        
        for i in range(n_particles):
            # Random position within dispersal radius
            angle = np.random.uniform(0, 2*np.pi)
            radius = np.random.exponential(self.dispersal_radius/3)
            
            x = self.initial_position[0] + radius * np.cos(angle)
            y = self.initial_position[1] + radius * np.sin(angle)
            
            particle = SimulationState(
                x=x,
                y=y,
                vx=np.random.normal(0, 0.05),  # Small random currents
                vy=np.random.normal(0, 0.05),
                depth=0.0,
                properties={
                    'type': 'person_in_water',
                    'particle_id': i,
                    'survival_hours': 12  # Hypothermia onset
                }
            )
            particles.append(particle)
        
        return particles
    
    def simulate(self, duration_hours: float = 24,
                 weather: str = 'moderate',
                 n_particles: int = 100) -> Dict[str, Any]:
        """
        Run PIW drift simulation
        
        Args:
            duration_hours: Simulation duration in hours
            weather: 'calm', 'moderate', or 'severe'
            n_particles: Number of particles to simulate
        
        Returns:
            Simulation results with search grid recommendations
        """
        # Environmental conditions by weather
        weather_profiles = {
            'calm': {
                'wind_x': 0.2,
                'wind_y': 0.1,
                'current_x': 0.1,
                'current_y': 0.05,
                'description': 'Light winds, minimal current'
            },
            'moderate': {
                'wind_x': 0.6,
                'wind_y': 0.4,
                'current_x': 0.25,
                'current_y': -0.15,
                'description': 'Moderate winds, typical current'
            },
            'severe': {
                'wind_x': 1.5,
                'wind_y': 1.0,
                'current_x': 0.5,
                'current_y': -0.3,
                'description': 'Strong winds, challenging conditions'
            }
        }
        
        environment = weather_profiles.get(weather, weather_profiles['moderate'])
        
        # Create particles
        particles = self._create_scattered_particles(n_particles)
        
        # Run simulation
        processor = BatchProcessor(physics_model=WaterDriftModel())
        processor.add_particles(particles)
        processor.set_environment({k: v for k, v in environment.items() 
                                  if k in ['wind_x', 'wind_y', 'current_x', 'current_y']})
        
        duration_seconds = duration_hours * 3600
        results = processor.run(duration=duration_seconds, dt=60.0, batch_size=50)
        
        # Calculate search grid
        positions = results['all_final_positions']
        x_coords = np.array([p['x'] for p in positions])
        y_coords = np.array([p['y'] for p in positions])
        
        center_x, center_y = np.mean(x_coords), np.mean(y_coords)
        std_x, std_y = np.std(x_coords), np.std(y_coords)
        
        return {
            'scenario': 'Person in Water',
            'duration_hours': duration_hours,
            'weather': weather,
            'weather_description': environment['description'],
            'particles_simulated': n_particles,
            'search_center': (center_x, center_y),
            'search_radius_1_sigma': np.sqrt(std_x**2 + std_y**2),
            'search_radius_2_sigma': 2 * np.sqrt(std_x**2 + std_y**2),
            'search_radius_3_sigma': 3 * np.sqrt(std_x**2 + std_y**2),
            'final_positions': positions,
            'recommended_search_grid': {
                'center_lat': center_x,
                'center_lon': center_y,
                'primary_search_radius_nm': np.sqrt(std_x**2 + std_y**2) * 60,  # Approx miles
                'secondary_search_radius_nm': 2 * np.sqrt(std_x**2 + std_y**2) * 60,
                'coverage_probability_primary': 0.68,
                'coverage_probability_secondary': 0.95,
                'recommendation': f'Search {np.sqrt(std_x**2 + std_y**2):.3f} degrees from center'
            }
        }


class VesselIncidentSimulation:
    """Simulate vessel-related SAR incidents (sinking, disabled vessel, etc)"""
    
    def __init__(self, initial_lat: float, initial_lon: float,
                 vessel_type: str = 'small_boat'):
        """
        Initialize vessel incident simulation
        
        Args:
            initial_lat: Incident latitude
            initial_lon: Incident longitude
            vessel_type: 'small_boat', 'fishing_vessel', 'cargo_ship', etc
        """
        self.initial_position = (initial_lat, initial_lon)
        self.vessel_type = vessel_type
        
        # Different dispersal patterns by vessel type
        self.dispersal_patterns = {
            'small_boat': {'radius': 0.01, 'n_debris': 50},
            'fishing_vessel': {'radius': 0.05, 'n_debris': 200},
            'cargo_ship': {'radius': 0.1, 'n_debris': 500},
            'liferaft': {'radius': 0.001, 'n_debris': 1}
        }
    
    def _create_debris_field(self, n_particles: int) -> List[SimulationState]:
        """Create debris field particles"""
        particles = []
        pattern = self.dispersal_patterns.get(self.vessel_type, 
                                             self.dispersal_patterns['small_boat'])
        
        for i in range(n_particles):
            angle = np.random.uniform(0, 2*np.pi)
            radius = np.random.uniform(0, pattern['radius'])
            
            x = self.initial_position[0] + radius * np.cos(angle)
            y = self.initial_position[1] + radius * np.sin(angle)
            
            particle = SimulationState(
                x=x,
                y=y,
                vx=np.random.normal(0, 0.1),
                vy=np.random.normal(0, 0.1),
                depth=0.0,
                properties={
                    'type': 'debris',
                    'vessel_type': self.vessel_type,
                    'particle_id': i
                }
            )
            particles.append(particle)
        
        return particles
    
    def simulate_multi_weather(self, duration_hours: float = 24) -> Dict[str, Any]:
        """
        Simulate vessel incident under multiple weather scenarios
        
        Helps determine worst-case search area
        """
        scenarios = ['calm', 'moderate', 'severe']
        scenario_results = {}
        
        for weather in scenarios:
            # Similar to PIW simulation
            particles = self._create_debris_field(100)
            
            processor = BatchProcessor(physics_model=WaterDriftModel())
            processor.add_particles(particles)
            
            # Weather conditions
            weather_env = {
                'calm': {'wind_x': 0.2, 'wind_y': 0.1, 'current_x': 0.1, 'current_y': 0.05},
                'moderate': {'wind_x': 0.6, 'wind_y': 0.4, 'current_x': 0.25, 'current_y': -0.15},
                'severe': {'wind_x': 1.5, 'wind_y': 1.0, 'current_x': 0.5, 'current_y': -0.3}
            }
            
            processor.set_environment(weather_env[weather])
            results = processor.run(duration=duration_hours*3600, dt=60.0, batch_size=50)
            
            positions = results['all_final_positions']
            x_coords = np.array([p['x'] for p in positions])
            y_coords = np.array([p['y'] for p in positions])
            
            scenario_results[weather] = {
                'spread': np.sqrt(np.var(x_coords) + np.var(y_coords)),
                'center': (np.mean(x_coords), np.mean(y_coords)),
                'radius': np.sqrt(np.std(x_coords)**2 + np.std(y_coords)**2)
            }
        
        return {
            'vessel_type': self.vessel_type,
            'scenarios': scenario_results,
            'worst_case_radius': max(s['radius'] for s in scenario_results.values()),
            'recommendation': 'Use worst-case scenario for comprehensive search grid'
        }


class SearchGridPlanner:
    """
    Generate SAR search grids from simulation results
    
    Converts drift predictions into standardized search patterns
    """
    
    @staticmethod
    def expanding_square(center: Tuple[float, float],
                        initial_radius: float,
                        grid_spacing: float = 0.01) -> List[Tuple[float, float]]:
        """
        Generate expanding square search pattern
        
        Args:
            center: Search center (lat, lon)
            initial_radius: Starting search radius
            grid_spacing: Distance between search lines
        
        Returns:
            List of waypoints for search pattern
        """
        waypoints = []
        
        # Create square grids at expanding distances
        for expansion in range(int(initial_radius / grid_spacing)):
            radius = grid_spacing * expansion
            
            # Create 4-point square
            for corner in range(4):
                offset_x = radius if corner % 2 == 0 else -radius
                offset_y = radius if corner // 2 == 0 else -radius
                
                waypoints.append((
                    center[0] + offset_x,
                    center[1] + offset_y
                ))
        
        return waypoints
    
    @staticmethod
    def parallel_track(center: Tuple[float, float],
                      search_radius: float,
                      track_spacing: float = 0.01) -> List[Tuple[float, float]]:
        """
        Generate parallel track search pattern
        
        Args:
            center: Search center
            search_radius: Search area radius
            track_spacing: Distance between parallel tracks
        
        Returns:
            List of waypoints
        """
        waypoints = []
        
        # Parallel tracks across search area
        for y_offset in np.arange(-search_radius, search_radius, track_spacing):
            # Alternating direction for efficiency
            if int(y_offset / track_spacing) % 2 == 0:
                x_range = np.linspace(-search_radius, search_radius, 20)
            else:
                x_range = np.linspace(search_radius, -search_radius, 20)
            
            for x_offset in x_range:
                waypoints.append((
                    center[0] + x_offset,
                    center[1] + y_offset
                ))
        
        return waypoints
    
    @staticmethod
    def probability_weighting(center: Tuple[float, float],
                            positions: List[Dict],
                            grid_x: int = 20,
                            grid_y: int = 20) -> np.ndarray:
        """
        Generate probability heatmap for search area
        
        Args:
            center: Search center
            positions: Final particle positions from simulation
            grid_x: Grid width
            grid_y: Grid height
        
        Returns:
            2D probability array (normalized 0-1)
        """
        # Extract coordinates
        x_coords = np.array([p['x'] for p in positions])
        y_coords = np.array([p['y'] for p in positions])
        
        # Calculate bounds
        x_min, x_max = np.min(x_coords), np.max(x_coords)
        y_min, y_max = np.min(y_coords), np.max(y_coords)
        
        # Create grid
        heatmap = np.zeros((grid_y, grid_x))
        
        x_edges = np.linspace(x_min, x_max, grid_x + 1)
        y_edges = np.linspace(y_min, y_max, grid_y + 1)
        
        # Populate heatmap
        for x, y in zip(x_coords, y_coords):
            xi = int((x - x_min) / (x_max - x_min) * grid_x)
            yi = int((y - y_min) / (y_max - y_min) * grid_y)
            
            if 0 <= xi < grid_x and 0 <= yi < grid_y:
                heatmap[yi, xi] += 1.0
        
        # Normalize
        heatmap = heatmap / np.sum(heatmap) if np.sum(heatmap) > 0 else heatmap
        
        return heatmap


def demo_sar_scenarios():
    """Demonstrate various SAR simulation scenarios"""
    
    print("\n" + "="*60)
    print("CesarOps SAR Simulation Scenarios")
    print("="*60)
    
    # Scenario 1: Person in water
    print("\n[Scenario 1] Person in Water (PIW) - 24 Hour Simulation")
    print("-" * 60)
    
    piw = PersonInWaterSimulation(41.123, -71.456)
    piw_result = piw.simulate(duration_hours=24, weather='moderate', n_particles=50)
    
    print(f"Location: {piw_result['search_center']}")
    print(f"Primary search radius: {piw_result['search_radius_1_sigma']:.4f} degrees")
    print(f"Secondary search radius: {piw_result['search_radius_2_sigma']:.4f} degrees")
    print(f"Weather: {piw_result['weather_description']}")
    print(f"Recommended action: {piw_result['recommended_search_grid']['recommendation']}")
    
    # Scenario 2: Vessel incident with multiple weather
    print("\n[Scenario 2] Small Vessel Incident - Multi-Weather Analysis")
    print("-" * 60)
    
    vessel = VesselIncidentSimulation(41.123, -71.456, vessel_type='small_boat')
    vessel_result = vessel.simulate_multi_weather(duration_hours=24)
    
    print(f"Vessel type: {vessel_result['vessel_type']}")
    print(f"Worst-case search radius: {vessel_result['worst_case_radius']:.4f} degrees")
    print("Scenario breakdown:")
    for weather, data in vessel_result['scenarios'].items():
        print(f"  {weather:10} -> Radius: {data['radius']:.4f} degrees, "
              f"Center: ({data['center'][0]:.6f}, {data['center'][1]:.6f})")
    
    # Scenario 3: Search grid generation
    print("\n[Scenario 3] Search Grid Planning")
    print("-" * 60)
    
    planner = SearchGridPlanner()
    
    # Expanding square pattern
    center = (41.123, -71.456)
    square_grid = planner.expanding_square(center, initial_radius=0.05)
    print(f"Expanding square pattern: {len(square_grid)} waypoints")
    print(f"  First 3 waypoints: {square_grid[:3]}")
    
    # Parallel track pattern
    parallel_grid = planner.parallel_track(center, search_radius=0.05)
    print(f"\nParallel track pattern: {len(parallel_grid)} waypoints")
    print(f"  First 3 waypoints: {parallel_grid[:3]}")
    
    # Probability heatmap
    positions = piw_result['final_positions']
    heatmap = planner.probability_weighting(center, positions, grid_x=10, grid_y=10)
    print(f"\nProbability heatmap generated: {heatmap.shape}")
    print(f"  Max probability: {np.max(heatmap):.4f}")
    print(f"  Areas with >10% probability: {np.sum(heatmap > 0.1)}")
    
    print("\n" + "="*60)
    print("✅ SAR scenario demonstrations complete!")
    print("="*60)


if __name__ == "__main__":
    demo_sar_scenarios()
