import random

class PreventionAlgorithm:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.resource_order = {}
        
    def init_resource_ordering(self, resources):
        """Initialize resource ordering for prevention"""
        self.resource_order = {}
        for i, rtype in enumerate(resources.keys()):
            self.resource_order[rtype] = i + 1

    def check_prevention_rule(self, process, resource_type):
        """Check if request violates resource ordering rule"""
        if not process.held_resources:
            return True
            
        max_held_order = max([self.resource_order[rt] for rt in process.held_resources])
        return self.resource_order[resource_type] > max_held_order

    def handle_request(self, process, resource_type, units):
        """Handle request in prevention mode"""
        if not self.check_prevention_rule(process, resource_type):
            process.deny_resource()
            self.coordinator.preventions += 1
            return "DENIED - Violates resource ordering rule"
        
        resource = self.coordinator.resources[resource_type]
        if resource.can_allocate(units):
            resource.allocate(process.pid, units)
            process.grant_resource(resource_type, units)
            return "GRANTED - Follows resource ordering"
        else:
            self.coordinator.waiting_requests.append((process, resource_type, units))
            return "WAITING - Resource not available"