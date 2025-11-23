import copy
import random
from banker import BankerAlgorithm
from detection import DeadlockDetection
from prevention import PreventionAlgorithm
from resource import Resource
from process import Process

try:
    from logger_config import log_info, log_warning, log_error, log_debug
except ImportError:
    # Fallback if logger not available
    def log_info(msg): print(f"[INFO] {msg}")
    def log_warning(msg): print(f"[WARNING] {msg}")
    def log_error(msg): print(f"[ERROR] {msg}")
    def log_debug(msg): print(f"[DEBUG] {msg}")

class Coordinator:
    def __init__(self, gui_update_callback):
        self.processes = {}
        self.resources = {}
        self.gui_update_callback = gui_update_callback
        self.waiting_requests = []  # List of (process, resource_type, units)
        self.mode = "detection"  # prevention, avoidance, detection
        self.current_step = 0
        self.running = False
        
        # Statistics
        self.deadlocks_detected = 0
        self.recoveries = 0
        self.requests_made = 0
        self.preventions = 0
        self.avoidances = 0
        
        # Algorithm modules
        self.banker = BankerAlgorithm(self)
        self.detection = DeadlockDetection(self)
        self.prevention = PreventionAlgorithm(self)
        
    def setup_custom_system(self, num_processes, num_resources):
        """Setup system with custom number of processes and resources"""
        try:
            if num_processes < 1 or num_processes > 100:
                log_warning(f"Invalid process count: {num_processes}, clamping to 1-100")
                num_processes = max(1, min(100, num_processes))
            
            if num_resources < 1 or num_resources > 100:
                log_warning(f"Invalid resource count: {num_resources}, clamping to 1-100")
                num_resources = max(1, min(100, num_resources))
            
            self.processes = {}
            self.resources = {}
            
            # Create resources
            for i in range(num_resources):
                rid = f"R{i}"
                self.resources[rid] = Resource(rid, random.randint(2, 4))
                
            # Initialize prevention ordering
            self.prevention.init_resource_ordering(self.resources)
                
            # Create processes
            for i in range(num_processes):
                pid = f"P{i}"
                self.add_process(pid)
                
            self.banker.init_banker_data()
            log_info(f"System setup: {num_processes} processes, {num_resources} resources")
        except Exception as e:
            log_error(f"Error setting up system: {str(e)}")
            raise
        
    def add_process(self, pid):
        if pid not in self.processes:
            self.processes[pid] = Process(pid, self, self.gui_update_callback)
            if self.mode == "avoidance":
                self.banker.init_process_banker_data(pid)
                
    def set_mode(self, mode):
        self.mode = mode
        if mode == "avoidance":
            self.banker.init_banker_data()

    def request_resource(self, process, resource_type, units):
        """Handle resource request based on current mode"""
        try:
            if not process or resource_type not in self.resources or units < 1:
                log_warning(f"Invalid request: process={process}, resource={resource_type}, units={units}")
                return "ERROR - Invalid request parameters"
            
            self.current_step += 1
            self.requests_made += 1
            result = None
            
            if self.mode == "prevention":
                result = self.prevention.handle_request(process, resource_type, units)
            elif self.mode == "avoidance":
                result = self.banker.handle_request(process, resource_type, units)
            else:  # detection mode
                result = self._handle_detection_request(process, resource_type, units)
            
            log_debug(f"Request result: {result}")
            if self.gui_update_callback:
                self.gui_update_callback()
            return result
        except Exception as e:
            log_error(f"Error in request_resource: {str(e)}")
            return f"ERROR - {str(e)}"

    def _handle_detection_request(self, process, resource_type, units):
        """Handle request in detection mode"""
        resource = self.resources[resource_type]
        if resource.can_allocate(units):
            resource.allocate(process.pid, units)
            process.grant_resource(resource_type, units)
            return "GRANTED"
        else:
            self.waiting_requests.append((process, resource_type, units))
            return "WAITING - Resource not available"

    def release_resource(self, process, resource_type, units):
        """Release resources and handle waiting requests"""
        try:
            if resource_type not in self.resources:
                log_warning(f"Resource not found: {resource_type}")
                return "ERROR - Resource not found"
            
            if not process or units < 1:
                log_warning(f"Invalid release: process={process}, units={units}")
                return "ERROR - Invalid release parameters"
                
            resource = self.resources[resource_type]
            actual_released = resource.release(process.pid, units)
            
            if resource_type in process.held_resources:
                process.held_resources[resource_type] -= actual_released
                if process.held_resources[resource_type] <= 0:
                    del process.held_resources[resource_type]
                    if resource_type in process.holding:
                        process.holding.remove(resource_type)
            
            # Update Banker's algorithm data if in avoidance mode
            if self.mode == "avoidance" and process.pid in self.banker.allocation:
                self.banker.allocation[process.pid][resource_type] -= actual_released
                self.banker.available[resource_type] += actual_released
            
            # Check waiting requests that can now be granted
            self._check_waiting_requests()
            if self.gui_update_callback:
                self.gui_update_callback()
            
            log_debug(f"Released {actual_released} units of {resource_type} from {process.pid}")
            return f"RELEASED {actual_released} units of {resource_type}"
        except Exception as e:
            log_error(f"Error in release_resource: {str(e)}")
            return f"ERROR - {str(e)}"

    def _check_waiting_requests(self):
        """Check if any waiting requests can now be granted"""
        granted_requests = []
        
        for i, (process, resource_type, units) in enumerate(self.waiting_requests):
            if process.state == "terminated":
                continue
                
            resource = self.resources[resource_type]
            
            if self.mode == "avoidance":
                if (units <= self.banker.available[resource_type] and 
                    self.banker.is_safe_state(process.pid, resource_type, units)):
                    # Grant in avoidance mode
                    self.banker.available[resource_type] -= units
                    self.banker.allocation[process.pid][resource_type] += units
                    self.banker.need[process.pid][resource_type] -= units
                    resource.allocate(process.pid, units)
                    process.grant_resource(resource_type, units)
                    granted_requests.append(i)
            else:
                if resource.can_allocate(units):
                    # Grant in prevention/detection mode
                    resource.allocate(process.pid, units)
                    process.grant_resource(resource_type, units)
                    granted_requests.append(i)
        
        # Remove granted requests from waiting list
        for i in sorted(granted_requests, reverse=True):
            if i < len(self.waiting_requests):
                del self.waiting_requests[i]

    def auto_step(self):
        """Perform an automatic simulation step"""
        try:
            if not self.processes:
                log_warning("No processes available for auto step")
                return "No processes available"
                
            # Select a random process that's not terminated
            available_processes = [p for p in self.processes.values() 
                                 if p.state != "terminated" and p.state != "waiting"]
            if not available_processes:
                log_debug("All processes are terminated or waiting")
                return "All processes are terminated or waiting"
                
            process = random.choice(available_processes)
            
            # Random action: request (70%), release (30%)
            if random.random() < 0.7 and self.resources:
                # Request action
                resource_type = random.choice(list(self.resources.keys()))
                max_units = self.resources[resource_type].total_units
                units = random.randint(1, min(2, max_units))
                result = process.request_resource(resource_type, units)
                log_info(f"Auto: {process.pid} requested {units} of {resource_type}")
                return f"Auto: {process.pid} requested {units} of {resource_type}: {result}"
            else:
                # Release action
                if process.held_resources:
                    resource_type = random.choice(list(process.held_resources.keys()))
                    max_units = process.held_resources[resource_type]
                    units = random.randint(1, max_units)
                    result = process.release_resource(resource_type, units)
                    log_info(f"Auto: {process.pid} released {units} of {resource_type}")
                    return f"Auto: {process.pid} released {units} of {resource_type}"
                else:
                    return f"{process.pid} has no resources to release"
        except Exception as e:
            log_error(f"Error in auto_step: {str(e)}")
            return f"ERROR - {str(e)}"

    def get_system_state(self):
        """Get current system state for display"""
        state = {
            'processes': {},
            'resources': {},
            'waiting_requests': [],
            'banker_data': None,
            'statistics': {
                'deadlocks_detected': self.deadlocks_detected,
                'recoveries': self.recoveries,
                'requests_made': self.requests_made,
                'preventions': self.preventions,
                'avoidances': self.avoidances
            }
        }
        
        for pid, process in self.processes.items():
            state['processes'][pid] = {
                'state': process.state,
                'held_resources': process.held_resources.copy(),
                'waiting_for': process.waiting_for,
                'requesting': process.requesting,
                'holding': process.holding.copy(),
                'color': process.color,
                'required_resources': getattr(process, 'required_resources', {}).copy()
            }
            
        for rtype, resource in self.resources.items():
            state['resources'][rtype] = {
                'total': resource.total_units,
                'available': resource.available_units,
                'allocated': resource.allocated.copy()
            }
            
        state['waiting_requests'] = [(p.pid, rt, u) for p, rt, u in self.waiting_requests]
        
        if self.mode == "avoidance":
            state['banker_data'] = {
                'available': self.banker.available.copy(),
                'allocation': copy.deepcopy(self.banker.allocation),
                'need': copy.deepcopy(self.banker.need)
            }
            
        return state