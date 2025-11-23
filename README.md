# 🛜 Distributed Deadlock Simulation

A comprehensive web-based simulation platform for understanding and visualizing distributed deadlock detection, prevention, and avoidance algorithms.

## Features

- **Three Deadlock Modes:**
  - 🔍 **Detection**: Monitor and detect circular wait conditions using cycle detection
  - 🛡️ **Prevention**: Prevent deadlocks using resource ordering
  - 🎯 **Avoidance**: Use Banker's Algorithm to maintain safe states

- **Network Simulation:**
  - Single node pair simulation
  - Multi-node network simulation over WiFi/LAN
  - Real-time connection status monitoring

- **Visualization:**
  - Interactive resource allocation graph
  - Process state tracking (ready, running, waiting, terminated)
  - Resource utilization charts
  - Live statistics dashboard

- **Algorithms Implemented:**
  - DFS-based cycle detection
  - Resource ordering prevention
  - Banker's Algorithm for avoidance
  - Process and resource management

## Requirements

- Python 3.8+
- Windows, Linux, or macOS

## Installation

### 1. Clone or download the project

```bash
cd d:\project\os_streamlit
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install streamlit==1.28.1 pandas==2.1.3 plotly==5.18.0 numpy==1.24.3 python-dotenv==1.0.0
```

## Quick Start

### Windows (Batch File)
```bash
run.bat
```

The app will open at `http://localhost:8503`

### Manual Start
```bash
streamlit run app.py
```

## Usage

### 1. Configuration Page
- Select connection mode (Single Node Pair or Multiple Nodes)
- Enter node ID, IP address, and port
- Set number of processes and resources
- Click "Start Simulation"

### 2. Simulation Page
- **Resource Operations:**
  - Request Resource: Send resource request to peer
  - Release Resource: Release held resources

- **Auto-Pilot:** Automatically step through simulation
- **Pause/Resume:** Control simulation flow
- **Mode Selection:** Switch between Detection, Prevention, and Avoidance

- **Monitoring:**
  - View resource allocation graph
  - Track statistics (requests, grants, denials, deadlocks, etc.)
  - Monitor connection status
  - Review activity logs

### 3. Multi-Node Setup (WiFi)

**On Each System:**
1. Find your IP address:
   - Windows: `ipconfig` → Look for IPv4 Address (e.g., 192.168.1.100)
   - Linux/Mac: `ifconfig` or `ip addr`

2. Ensure all systems are on the same WiFi network

3. Configure in the app:
   - Enter your IP address (not 127.0.0.1)
   - Choose unique ports for each system
   - Set total number of systems

4. Allow Python through firewall if prompted

## Project Structure

```
os_streamlit/
├── app.py                 # Main Streamlit application
├── coordinator.py         # System coordination and process management
├── detection.py          # Deadlock detection algorithm (DFS cycle detection)
├── prevention.py         # Deadlock prevention (resource ordering)
├── banker.py             # Deadlock avoidance (Banker's Algorithm)
├── process.py            # Process class and state management
├── resource.py           # Resource allocation and tracking
├── requirements.txt      # Python dependencies
├── run.bat              # Windows startup script
├── setup_firewall.ps1   # Windows firewall configuration
└── README.md            # This file
```

## Algorithm Details

### Detection Mode
- Builds a wait-for graph showing dependencies between processes
- Uses Depth-First Search (DFS) to detect cycles
- Initiates recovery by terminating a process in the cycle
- Suitable for systems that can tolerate deadlocks

### Prevention Mode
- Enforces resource ordering constraint
- Processes must request resources in increasing order
- Prevents circular wait condition
- Lower resource utilization but guarantees deadlock-free operation

### Avoidance Mode
- Implements Banker's Algorithm
- Maintains system in safe states
- Checks if resource allocation leaves system in safe state
- Maximum process demand must be declared in advance

## Statistics Tracked

- **Requests**: Total resource requests made
- **Grants**: Successfully allocated resources
- **Denials**: Requests denied due to prevention rules
- **Deadlocks**: Circular waits detected
- **Recoveries**: Deadlock recovery operations
- **Prevented**: Requests blocked by prevention algorithm
- **Avoided**: Requests handled by avoidance algorithm
- **Releases**: Resource releases completed

## Troubleshooting

### "Connection Refused" Error
- Check if peer node is running on correct IP and port
- Verify firewall isn't blocking the ports
- Ensure both systems are on same network (for WiFi setup)

### Slider Values Not Persisting
- Values are stored in session state
- Settings are applied when "Start Simulation" is clicked
- Adjust values before starting simulation

### Multi-Node Not Connecting
1. Test connectivity: Use "Test Network" button in configuration
2. Check local IP addresses with `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
3. Verify firewall rules allow Python
4. Ensure ports are in valid range (1024-65535)

### Application Crashes
- Check Python version: `python --version` (should be 3.8+)
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check logs for error messages

## Performance Notes

- Optimal simulation with 4-6 processes
- 2-3 processes for simple scenarios
- 8-10 processes for stress testing
- Graph rendering may slow down with many processes

## License

Educational project for deadlock algorithm understanding

## Author Notes

This project demonstrates:
- Operating system concepts (deadlock handling)
- Distributed systems principles
- Algorithm visualization
- Real-time system monitoring
- Multi-threaded simulation

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review algorithm documentation in source code
3. Enable debug logging by modifying app.py

---

**Last Updated**: November 22, 2025
