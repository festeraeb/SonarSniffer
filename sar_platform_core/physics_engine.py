"""
RK4-based Physics Engine for CesarOps SAR Platform

Implements 4th-order Runge-Kutta numerical integration for accurate
simulation of object trajectories in SAR scenarios (drift prediction,
search grid expansion, debris tracking, etc.)

Performance: 4th-order accuracy with ~4x overhead vs Euler method
Recommended for: Water current simulations, wind drift, multi-hour predictions
"""

import numpy as np
from dataclasses import dataclass
from typing import Callable, Tuple, List, Dict, Any
from abc import ABC, abstractmethod


@dataclass
class SimulationState:
    """Represents state of a single particle/object"""
    x: float  # Latitude or X coordinate
    y: float  # Longitude or Y coordinate
    vx: float  # X velocity
    vy: float  # Y velocity
    depth: float = 0.0  # Water depth (for buoyancy, current models)
    time: float = 0.0  # Elapsed simulation time
    properties: Dict[str, Any] = None  # Object-specific properties (type, mass, etc)
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array for RK4"""
        return np.array([self.x, self.y, self.vx, self.vy, self.depth])
    
    @staticmethod
    def from_array(arr: np.ndarray, properties: Dict = None) -> 'SimulationState':
        """Create from numpy array"""
        return SimulationState(
            x=float(arr[0]),
            y=float(arr[1]),
            vx=float(arr[2]),
            vy=float(arr[3]),
            depth=float(arr[4]) if len(arr) > 4 else 0.0,
            properties=properties or {}
        )


class PhysicsModel(ABC):
    """Base class for physics models used in RK4 solver"""
    
    @abstractmethod
    def acceleration(self, state: SimulationState, 
                    environmental_conditions: Dict) -> Tuple[float, float]:
        """
        Calculate acceleration (dvx/dt, dvy/dt) given current state
        
        Args:
            state: Current particle state
            environmental_conditions: Wind, current, temperature, etc
        
        Returns:
            (ax, ay): X and Y accelerations
        """
        pass
    
    @abstractmethod
    def velocity_update(self, state: SimulationState,
                       environmental_conditions: Dict) -> Tuple[float, float]:
        """
        Calculate velocity components (vx, vy) including environmental effects
        
        Args:
            state: Current particle state
            environmental_conditions: Wind, current, temperature, etc
        
        Returns:
            (vx, vy): Updated velocity components
        """
        pass


class WaterDriftModel(PhysicsModel):
    """Physics for floating objects in water with current and wind"""
    
    def __init__(self, wind_drag_coeff: float = 0.02,
                 current_drag_coeff: float = 0.01,
                 water_friction: float = 0.05):
        """
        Initialize water drift model
        
        Args:
            wind_drag_coeff: Wind drag coefficient (0.01-0.05 typical)
            current_drag_coeff: Current drag coefficient
            water_friction: Water resistance (0.01-0.1 typical)
        """
        self.wind_drag = wind_drag_coeff
        self.current_drag = current_drag_coeff
        self.friction = water_friction
    
    def acceleration(self, state: SimulationState,
                    environmental_conditions: Dict) -> Tuple[float, float]:
        """Calculate acceleration from drag forces"""
        # Wind effect (atmospheric drag)
        wind_x = environmental_conditions.get('wind_x', 0.0)
        wind_y = environmental_conditions.get('wind_y', 0.0)
        wind_speed = np.sqrt(wind_x**2 + wind_y**2)
        
        # Current effect
        current_x = environmental_conditions.get('current_x', 0.0)
        current_y = environmental_conditions.get('current_y', 0.0)
        
        # Relative velocity (wind relative to object)
        rel_wind_x = wind_x - state.vx
        rel_wind_y = wind_y - state.vy
        rel_wind_speed = np.sqrt(rel_wind_x**2 + rel_wind_y**2) + 1e-6
        
        # Relative velocity (current relative to object)
        rel_current_x = current_x - state.vx
        rel_current_y = current_y - state.vy
        
        # Drag forces
        if rel_wind_speed > 0:
            wind_force_x = self.wind_drag * rel_wind_x * rel_wind_speed
            wind_force_y = self.wind_drag * rel_wind_y * rel_wind_speed
        else:
            wind_force_x = wind_force_y = 0.0
        
        current_force_x = self.current_drag * rel_current_x
        current_force_y = self.current_drag * rel_current_y
        
        # Water friction opposing motion
        motion_speed = np.sqrt(state.vx**2 + state.vy**2) + 1e-6
        friction_x = -self.friction * state.vx * motion_speed
        friction_y = -self.friction * state.vy * motion_speed
        
        # Total acceleration (F = ma, assuming unit mass)
        ax = wind_force_x + current_force_x + friction_x
        ay = wind_force_y + current_force_y + friction_y
        
        return (ax, ay)
    
    def velocity_update(self, state: SimulationState,
                       environmental_conditions: Dict) -> Tuple[float, float]:
        """For this model, velocity is state.vx, state.vy"""
        return (state.vx, state.vy)


class SubmersibleModel(PhysicsModel):
    """Physics for submerged objects affected by depth-dependent currents"""
    
    def __init__(self, buoyancy_adjustment: float = 0.0,
                 depth_current_factor: float = 0.8):
        """
        Initialize submersible/submerged object model
        
        Args:
            buoyancy_adjustment: Vertical velocity from buoyancy (m/s)
            depth_current_factor: How much current varies with depth (0-1)
        """
        self.buoyancy = buoyancy_adjustment
        self.depth_factor = depth_current_factor
    
    def acceleration(self, state: SimulationState,
                    environmental_conditions: Dict) -> Tuple[float, float]:
        """Calculate acceleration with depth-dependent effects"""
        # Get base current
        current_x = environmental_conditions.get('current_x', 0.0)
        current_y = environmental_conditions.get('current_y', 0.0)
        
        # Depth modulation (deeper = weaker current)
        max_depth = environmental_conditions.get('max_depth', 100.0)
        depth_factor = max(0.1, 1.0 - (state.depth / max_depth) * self.depth_factor)
        
        current_x *= depth_factor
        current_y *= depth_factor
        
        # Simple drag model
        ax = -0.1 * state.vx + current_x * 0.01
        ay = -0.1 * state.vy + current_y * 0.01
        
        return (ax, ay)
    
    def velocity_update(self, state: SimulationState,
                       environmental_conditions: Dict) -> Tuple[float, float]:
        return (state.vx, state.vy)


class RK4Integrator:
    """
    4th-order Runge-Kutta ODE solver for SAR simulations
    
    Solves systems of ODEs:
        dx/dt = vx
        dy/dt = vy
        dvx/dt = acceleration_x(...)
        dvy/dt = acceleration_y(...)
    """
    
    def __init__(self, physics_model: PhysicsModel):
        """
        Initialize integrator with physics model
        
        Args:
            physics_model: PhysicsModel instance defining system behavior
        """
        self.physics = physics_model
    
    def _derivatives(self, state: SimulationState,
                    environmental_conditions: Dict) -> np.ndarray:
        """
        Calculate derivatives: [dx/dt, dy/dt, dvx/dt, dvy/dt, ...]
        
        Args:
            state: Current state
            environmental_conditions: Environmental parameters
        
        Returns:
            numpy array of derivatives
        """
        ax, ay = self.physics.acceleration(state, environmental_conditions)
        
        return np.array([
            state.vx,  # dx/dt = vx
            state.vy,  # dy/dt = vy
            ax,        # dvx/dt = ax
            ay,        # dvy/dt = ay
            0.0        # depth stays constant (no vertical motion)
        ])
    
    def step(self, state: SimulationState, dt: float,
            environmental_conditions: Dict) -> SimulationState:
        """
        Perform single RK4 integration step
        
        Args:
            state: Current state
            dt: Time step (seconds)
            environmental_conditions: Environmental parameters
        
        Returns:
            Updated state after one time step
        """
        # Initial state as array
        y = state.to_array()
        
        # RK4 coefficients
        k1 = self._derivatives(state, environmental_conditions)
        
        # k2: state at t + dt/2 using k1
        y2 = y + 0.5 * dt * k1
        state2 = SimulationState.from_array(y2, state.properties.copy())
        k2 = self._derivatives(state2, environmental_conditions)
        
        # k3: state at t + dt/2 using k2
        y3 = y + 0.5 * dt * k2
        state3 = SimulationState.from_array(y3, state.properties.copy())
        k3 = self._derivatives(state3, environmental_conditions)
        
        # k4: state at t + dt using k3
        y4 = y + dt * k3
        state4 = SimulationState.from_array(y4, state.properties.copy())
        k4 = self._derivatives(state4, environmental_conditions)
        
        # Weighted average of slopes
        y_new = y + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
        
        # Create new state
        new_state = SimulationState.from_array(y_new, state.properties.copy())
        new_state.time = state.time + dt
        
        return new_state
    
    def integrate(self, initial_state: SimulationState, duration: float,
                 dt: float, environmental_conditions: Dict) -> List[SimulationState]:
        """
        Integrate trajectory over time period
        
        Args:
            initial_state: Starting position/velocity
            duration: Total simulation time (seconds)
            dt: Time step (seconds)
            environmental_conditions: Environmental parameters dict
        
        Returns:
            List of states at each time step
        """
        states = [initial_state]
        current_state = initial_state
        current_time = 0.0
        
        steps = int(duration / dt)
        for _ in range(steps):
            current_state = self.step(current_state, dt, environmental_conditions)
            states.append(current_state)
            current_time += dt
        
        return states


class SARODESystem:
    """
    Combined ODE system for SAR simulations
    
    Handles multiple particles/objects with RK4 integration,
    tracks environmental conditions, manages simulation state.
    """
    
    def __init__(self, physics_model: PhysicsModel):
        """
        Initialize SAR ODE system
        
        Args:
            physics_model: PhysicsModel instance
        """
        self.integrator = RK4Integrator(physics_model)
        self.particles: List[SimulationState] = []
        self.environmental_conditions: Dict[str, float] = {}
        self.trajectories: Dict[int, List[SimulationState]] = {}
    
    def add_particle(self, particle: SimulationState) -> int:
        """Add particle to simulation"""
        idx = len(self.particles)
        self.particles.append(particle)
        self.trajectories[idx] = [particle]
        return idx
    
    def set_environment(self, conditions: Dict[str, float]):
        """Set environmental parameters (wind, current, etc)"""
        self.environmental_conditions = conditions
    
    def simulate(self, duration: float, dt: float = 1.0) -> Dict[int, List[SimulationState]]:
        """
        Run simulation for all particles
        
        Args:
            duration: Total simulation time (seconds)
            dt: Time step (seconds)
        
        Returns:
            Dictionary mapping particle index to trajectory
        """
        for idx, particle in enumerate(self.particles):
            trajectory = self.integrator.integrate(
                particle, duration, dt, self.environmental_conditions
            )
            self.trajectories[idx] = trajectory
        
        return self.trajectories
    
    def get_final_positions(self) -> List[Tuple[float, float]]:
        """Get final position of each particle"""
        positions = []
        for idx in range(len(self.particles)):
            if self.trajectories[idx]:
                final_state = self.trajectories[idx][-1]
                positions.append((final_state.x, final_state.y))
        return positions
    
    def get_heatmap_data(self, grid_x: int = 100, grid_y: int = 100,
                         x_bounds: Tuple[float, float] = None,
                         y_bounds: Tuple[float, float] = None) -> np.ndarray:
        """
        Generate heatmap of particle density over search area
        
        Args:
            grid_x: Grid width
            grid_y: Grid height
            x_bounds: (x_min, x_max) for grid
            y_bounds: (y_min, y_max) for grid
        
        Returns:
            2D numpy array (heatmap)
        """
        # Auto-detect bounds if not provided
        if x_bounds is None or y_bounds is None:
            all_x = []
            all_y = []
            for trajectory in self.trajectories.values():
                for state in trajectory:
                    all_x.append(state.x)
                    all_y.append(state.y)
            
            x_bounds = (min(all_x) - 0.1, max(all_x) + 0.1)
            y_bounds = (min(all_y) - 0.1, max(all_y) + 0.1)
        
        heatmap = np.zeros((grid_y, grid_x))
        
        x_edges = np.linspace(x_bounds[0], x_bounds[1], grid_x + 1)
        y_edges = np.linspace(y_bounds[0], y_bounds[1], grid_y + 1)
        
        # Accumulate particle positions into heatmap
        for trajectory in self.trajectories.values():
            for state in trajectory:
                try:
                    xi = np.searchsorted(x_edges, state.x) - 1
                    yi = np.searchsorted(y_edges, state.y) - 1
                    if 0 <= xi < grid_x and 0 <= yi < grid_y:
                        heatmap[yi, xi] += 1.0
                except (ValueError, IndexError):
                    pass
        
        return heatmap


def compare_integration_methods(duration: float = 3600.0, dt: float = 10.0) -> Dict[str, Any]:
    """
    Compare RK4 vs simple Euler method for accuracy demonstration
    
    Args:
        duration: Simulation duration (seconds)
        dt: Time step (seconds)
    
    Returns:
        Dictionary with comparison results
    """
    # Test particle
    initial = SimulationState(x=0.0, y=0.0, vx=0.1, vy=0.15, depth=0.0)
    
    # Environment
    env = {
        'wind_x': 0.5,
        'wind_y': 0.3,
        'current_x': 0.2,
        'current_y': -0.1
    }
    
    # RK4
    physics = WaterDriftModel()
    rk4 = RK4Integrator(physics)
    rk4_trajectory = rk4.integrate(initial, duration, dt, env)
    rk4_final = rk4_trajectory[-1]
    
    # Simple Euler for comparison
    euler_state = initial
    for _ in range(int(duration / dt)):
        ax, ay = physics.acceleration(euler_state, env)
        # Euler step
        new_x = euler_state.x + euler_state.vx * dt
        new_y = euler_state.y + euler_state.vy * dt
        new_vx = euler_state.vx + ax * dt
        new_vy = euler_state.vy + ay * dt
        
        euler_state = SimulationState(
            x=new_x, y=new_y, vx=new_vx, vy=new_vy,
            depth=euler_state.depth, time=euler_state.time + dt,
            properties=euler_state.properties
        )
    
    # Calculate error (distance between methods)
    error = np.sqrt((rk4_final.x - euler_state.x)**2 + 
                   (rk4_final.y - euler_state.y)**2)
    
    return {
        'duration': duration,
        'timestep': dt,
        'rk4_final_x': rk4_final.x,
        'rk4_final_y': rk4_final.y,
        'euler_final_x': euler_state.x,
        'euler_final_y': euler_state.y,
        'position_error': error,
        'rk4_steps': len(rk4_trajectory),
        'quality_metric': 'RK4 superior for large timesteps' if error > 0.1 else 'Both methods similar'
    }


if __name__ == "__main__":
    print("=" * 60)
    print("CesarOps SAR Physics Engine - RK4 Integration Test")
    print("=" * 60)
    
    # Test 1: Basic RK4 integration
    print("\n[Test 1] Basic RK4 Integration")
    print("-" * 60)
    
    physics = WaterDriftModel()
    initial_state = SimulationState(
        x=41.123,  # Latitude
        y=-71.456,  # Longitude
        vx=0.0,
        vy=0.0,
        depth=0.0,
        properties={'type': 'person', 'mass': 70}
    )
    
    environment = {
        'wind_x': 0.5,    # m/s wind in X
        'wind_y': 0.3,    # m/s wind in Y
        'current_x': 0.2,  # m/s current in X
        'current_y': -0.1  # m/s current in Y
    }
    
    integrator = RK4Integrator(physics)
    trajectory = integrator.integrate(initial_state, duration=3600.0, dt=60.0, 
                                     environmental_conditions=environment)
    
    print(f"Initial position: ({initial_state.x:.6f}, {initial_state.y:.6f})")
    print(f"Final position:   ({trajectory[-1].x:.6f}, {trajectory[-1].y:.6f})")
    print(f"Distance traveled: {np.sqrt((trajectory[-1].x - initial_state.x)**2 + (trajectory[-1].y - initial_state.y)**2):.4f}")
    print(f"Simulation steps: {len(trajectory)}")
    
    # Test 2: Multi-particle system
    print("\n[Test 2] Multi-Particle SAR Scenario")
    print("-" * 60)
    
    system = SARODESystem(WaterDriftModel())
    system.set_environment({
        'wind_x': 0.8,
        'wind_y': 0.5,
        'current_x': 0.3,
        'current_y': -0.2
    })
    
    # Add multiple particles (simulating debris field)
    np.random.seed(42)
    for i in range(10):
        particle = SimulationState(
            x=41.123 + np.random.normal(0, 0.001),
            y=-71.456 + np.random.normal(0, 0.001),
            vx=np.random.uniform(-0.1, 0.1),
            vy=np.random.uniform(-0.1, 0.1),
            properties={'particle_id': i}
        )
        system.add_particle(particle)
    
    trajectories = system.simulate(duration=7200.0, dt=60.0)
    
    print(f"Simulated {len(trajectories)} particles over 2 hours")
    print(f"Final positions:")
    for i, (x, y) in enumerate(system.get_final_positions()[:5]):
        print(f"  Particle {i}: ({x:.6f}, {y:.6f})")
    
    # Test 3: Method comparison
    print("\n[Test 3] RK4 vs Euler Comparison")
    print("-" * 60)
    
    comparison = compare_integration_methods(duration=3600.0, dt=10.0)
    print(f"RK4 final:    ({comparison['rk4_final_x']:.6f}, {comparison['rk4_final_y']:.6f})")
    print(f"Euler final:  ({comparison['euler_final_x']:.6f}, {comparison['euler_final_y']:.6f})")
    print(f"Position error: {comparison['position_error']:.6f} units")
    print(f"Quality: {comparison['quality_metric']}")
    
    print("\n" + "=" * 60)
    print("✅ Physics engine tests complete!")
    print("=" * 60)
