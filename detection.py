class DeadlockDetection:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        
    def build_wait_for_graph(self):
        """Build wait-for graph for deadlock detection"""
        graph = {pid: [] for pid in self.coordinator.processes}
        
        for process, resource_type, units in self.coordinator.waiting_requests:
            # Find processes holding the requested resource
            resource = self.coordinator.resources[resource_type]
            for holder_pid, held_units in resource.allocated.items():
                if held_units > 0 and holder_pid != process.pid:
                    graph[process.pid].append(holder_pid)
        
        return graph

    def find_cycle_dfs(self, graph):
        """Find cycle in wait-for graph using DFS"""
        visited = set()
        recursion_stack = set()
        
        def dfs(node, path):
            if node in recursion_stack:
                # Cycle found
                cycle_start = path.index(node)
                return path[cycle_start:]
            if node in visited:
                return None
                
            visited.add(node)
            recursion_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor in self.coordinator.processes:
                    result = dfs(neighbor, path.copy())
                    if result:
                        return result
            
            recursion_stack.remove(node)
            path.pop()
            return None
        
        for node in graph:
            if node not in visited:
                result = dfs(node, [])
                if result:
                    return result
        return None

    def detect_deadlock(self):
        """Detect deadlock and initiate recovery"""
        if self.coordinator.mode != "detection":
            return False
            
        graph = self.build_wait_for_graph()
        cycle = self.find_cycle_dfs(graph)
        
        if cycle:
            self.coordinator.deadlocks_detected += 1
            self.initiate_recovery(cycle)
            return True
        return False

    def initiate_recovery(self, cycle):
        """Recover from deadlock by terminating a process"""
        if not cycle:
            return
            
        # Terminate the first process in the cycle
        victim_pid = cycle[0]
        if victim_pid in self.coordinator.processes:
            victim = self.coordinator.processes[victim_pid]
            
            # Release all resources held by victim
            for resource_type, units in list(victim.held_resources.items()):
                self.coordinator.release_resource(victim, resource_type, units)
            
            victim.state = "terminated"
            self.coordinator.recoveries += 1
            
            # Remove waiting requests from victim
            self.coordinator.waiting_requests = [
                req for req in self.coordinator.waiting_requests 
                if req[0].pid != victim_pid
            ]