class Resource:
    def __init__(self, rid, total_units):
        self.id = rid
        self.rid = rid
        self.name = f"R{rid}"
        self.type = rid
        self.total_units = total_units
        self.available_units = total_units
        self.allocated = {}  # {process_id: units_allocated}

    def can_allocate(self, units):
        return self.available_units >= units

    def allocate(self, process_id, units):
        if self.can_allocate(units):
            self.available_units -= units
            if process_id in self.allocated:
                self.allocated[process_id] += units
            else:
                self.allocated[process_id] = units
            return True
        return False

    def release(self, process_id, units=None):
        if units is None:
            units = self.allocated.get(process_id, 0)
        
        if process_id in self.allocated:
            actual_units = min(units, self.allocated[process_id])
            self.available_units += actual_units
            self.allocated[process_id] -= actual_units
            if self.allocated[process_id] == 0:
                del self.allocated[process_id]
            return actual_units
        return 0