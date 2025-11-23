class Process:
    def __init__(self, pid, coordinator, gui_update_callback):
        self.id = pid
        self.pid = pid
        self.name = f"P{pid}"
        self.coordinator = coordinator
        self.gui_update_callback = gui_update_callback
        self.held_resources = {}  # {resource_type: units_held}
        self.holding = []  # List of resource IDs held (for visualization)
        self.waiting_for = None  # (resource_type, units)
        self.requesting = None  # Resource ID being requested (for visualization)
        self.state = "ready"  # ready, running, waiting, terminated
        self.color = self.get_process_color(pid)
        self.maximum = {}  # For Banker's algorithm
        self.required_resources = {}  # User-defined required resources
        
    def get_process_color(self, pid):
        # Dynamically generate a color based on pid index so we can support many processes.
        # pid may be like 'P0' or an integer; normalize to an index
        try:
            if isinstance(pid, str) and pid.startswith('P'):
                index = int(pid[1:])
            else:
                index = int(pid)
        except Exception:
            return "#CCCCCC"

        # Generate a color from HSV by varying the hue across processes
        # We choose up to 50 distinct hues (wrap if index > 49)
        max_colors = 50
        hue = (index % max_colors) / max_colors  # 0.0 - 1.0

        # Simple HSV to RGB conversion
        def hsv_to_hex(h, s=0.6, v=0.95):
            import colorsys
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            return '#{:02X}{:02X}{:02X}'.format(int(r*255), int(g*255), int(b*255))

        return hsv_to_hex(hue)
        
    def request_resource(self, resource_type, units):
        self.waiting_for = (resource_type, units)
        self.requesting = resource_type
        self.state = "waiting"
        return self.coordinator.request_resource(self, resource_type, units)
        
    def release_resource(self, resource_type, units=None):
        if units is None and resource_type in self.held_resources:
            units = self.held_resources[resource_type]
        return self.coordinator.release_resource(self, resource_type, units)
        
    def grant_resource(self, resource_type, units):
        if resource_type in self.held_resources:
            self.held_resources[resource_type] += units
        else:
            self.held_resources[resource_type] = units
        
        # Update holding list for visualization
        if resource_type not in self.holding:
            self.holding.append(resource_type)
            
        self.waiting_for = None
        self.requesting = None
        self.state = "running"
        
    def deny_resource(self):
        self.waiting_for = None
        self.requesting = None
        self.state = "ready"