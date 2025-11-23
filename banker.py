import copy
import random

class BankerAlgorithm:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.max_demand = {}
        self.allocation = {}
        self.need = {}
        self.available = {}
        
    def init_banker_data(self):
        """Initialize all Banker's algorithm data"""
        if not self.coordinator.resources:
            return
            
        self.available = {rtype: res.total_units for rtype, res in self.coordinator.resources.items()}
        self.allocation = {}
        self.max_demand = {}
        self.need = {}
        
        for pid in self.coordinator.processes:
            self.init_process_banker_data(pid)
            
    def init_process_banker_data(self, pid):
        """Initialize Banker's algorithm data for a process"""
        if not self.coordinator.resources:
            return
            
        self.allocation[pid] = {rtype: 0 for rtype in self.coordinator.resources}
        
        # Use user-defined requirements if available, otherwise generate random
        if hasattr(self.coordinator.processes[pid], 'required_resources') and self.coordinator.processes[pid].required_resources:
            self.max_demand[pid] = self.coordinator.processes[pid].required_resources.copy()
        else:
            self.max_demand[pid] = {
                rtype: random.randint(1, res.total_units) 
                for rtype, res in self.coordinator.resources.items()
            }
            
        self.need[pid] = copy.deepcopy(self.max_demand[pid])
        self.coordinator.processes[pid].maximum = self.max_demand[pid]
        
    def is_safe_state(self, process_id, resource_type, request_units):
        """Check if granting the request would leave system in safe state"""
        if not self.available or resource_type not in self.available:
            return False
            
        # Temporary state to test
        temp_available = copy.deepcopy(self.available)
        temp_allocation = copy.deepcopy(self.allocation)
        temp_need = copy.deepcopy(self.need)
        
        # Check if request is possible
        if (request_units > temp_available[resource_type] or 
            request_units > temp_need[process_id][resource_type]):
            return False
            
        # Pretend to allocate
        temp_available[resource_type] -= request_units
        temp_allocation[process_id][resource_type] += request_units
        temp_need[process_id][resource_type] -= request_units
        
        # Safety algorithm
        work = copy.deepcopy(temp_available)
        finish = {pid: False for pid in self.coordinator.processes}
        
        while True:
            found = False
            for pid in self.coordinator.processes:
                if not finish[pid]:
                    # Check if need <= work for all resources
                    can_allocate = all(
                        temp_need[pid][rtype] <= work[rtype] 
                        for rtype in self.coordinator.resources
                    )
                    if can_allocate:
                        # Process can finish - return its resources
                        for rtype in self.coordinator.resources:
                            work[rtype] += temp_allocation[pid][rtype]
                        finish[pid] = True
                        found = True
            
            if not found:
                break
        
        # System is safe if all processes can finish
        return all(finish.values())
        
    def handle_request(self, process, resource_type, units):
        """Handle request in avoidance mode using Banker's Algorithm"""
        pid = process.pid
        
        # Check if request exceeds max demand
        if units > self.need[pid][resource_type]:
            process.deny_resource()
            return "DENIED - Exceeds maximum demand"
            
        # Check if resources are available
        if units > self.available[resource_type]:
            self.coordinator.waiting_requests.append((process, resource_type, units))
            return "WAITING - Resource not available"
        
        # Check if state would be safe
        if self.is_safe_state(pid, resource_type, units):
            # Grant the request
            self.available[resource_type] -= units
            self.allocation[pid][resource_type] += units
            self.need[pid][resource_type] -= units
            self.coordinator.resources[resource_type].allocate(process.pid, units)
            process.grant_resource(resource_type, units)
            return "GRANTED - System remains in safe state"
        else:
            process.deny_resource()
            self.coordinator.avoidances += 1
            return "DENIED - Would lead to unsafe state"