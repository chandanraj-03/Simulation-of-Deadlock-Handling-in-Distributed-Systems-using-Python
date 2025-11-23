import streamlit as st
import time
import socket
import json
import threading
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# Import all the deadlock algorithm components
try:
    from coordinator import Coordinator
    from detection import DeadlockDetection
    from prevention import PreventionAlgorithm
    from banker import BankerAlgorithm
    from process import Process
    from resource import Resource
except ImportError as e:
    print(f"Warning: Could not import deadlock modules: {e}")

# Page configuration
st.set_page_config(
    page_title="Distributed Deadlock Simulation",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'simulation_started' not in st.session_state:
    st.session_state.simulation_started = False
    st.session_state.node_id = None
    st.session_state.my_ip = None
    st.session_state.my_port = None
    st.session_state.peer_ip = None
    st.session_state.peer_port = None
    st.session_state.resource = None
    st.session_state.num_processes = 4
    st.session_state.num_resources = 3
    st.session_state.logs = []
    st.session_state.stats = {
        "requests": 0,
        "deadlocks": 0,
        "recoveries": 0,
        "grants": 0,
        "denials": 0,
        "releases": 0,
        "preventions": 0,
        "avoidances": 0
    }
    st.session_state.mode = "detection"
    st.session_state.auto_pilot = False
    st.session_state.paused = False
    st.session_state.start_time = None
    st.session_state.connection_status = "Disconnected"
    st.session_state.resources_state = {}
    st.session_state.deadlock_cycle = []
    st.session_state.waiting_for = None
    st.session_state.server_running = False
    st.session_state.connected_nodes = []
    st.session_state.is_multi_node = False

def validate_ip_address(ip):
    """Validate IP address format"""
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False, "IP must have 4 parts separated by dots"
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False, f"Each IP part must be 0-255, got {num}"
        return True, "Valid IP"
    except ValueError:
        return False, "IP contains non-numeric values"

def validate_node_id(node_id):
    """Validate node ID format"""
    if not node_id or len(node_id) == 0:
        return False, "Node ID cannot be empty"
    if len(node_id) > 50:
        return False, "Node ID too long (max 50 characters)"
    if not node_id.replace('_', '').replace('-', '').isalnum():
        return False, "Node ID can only contain letters, numbers, hyphens, and underscores"
    return True, "Valid Node ID"

def validate_resource_name(resource):
    """Validate resource name format"""
    if not resource or len(resource) == 0:
        return False, "Resource name cannot be empty"
    if len(resource) > 10:
        return False, "Resource name too long (max 10 characters)"
    if not resource.isalnum():
        return False, "Resource name must be alphanumeric"
    return True, "Valid Resource"

def validate_port(port):
    """Validate port number"""
    if port < 1024 or port > 65535:
        return False, "Port must be between 1024 and 65535"
    return True, "Valid Port"

def log_message(msg):
    """Add message to logs with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {msg}")

def init_simulation():
    """Initialize the simulation"""
    st.session_state.simulation_started = True
    st.session_state.start_time = datetime.now()
    log_message("=" * 60)
    log_message("DISTRIBUTED DEADLOCK SIMULATION INITIALIZED")
    log_message("=" * 60)
    log_message(f"Node ID: {st.session_state.node_id}")
    log_message(f"Network: {st.session_state.my_ip}:{st.session_state.my_port}")
    log_message(f"Peer: {st.session_state.peer_ip}:{st.session_state.peer_port}")
    log_message(f"Resource: {st.session_state.resource}")
    log_message("")

def initialize_resources():
    """Initialize resources"""
    resource_types = ["CPU", "Memory", "I/O"]
    st.session_state.resources_state = {}
    
    for i in range(st.session_state.num_resources):
        resource_name = f"R{i+1}"
        resource_type = resource_types[i % len(resource_types)]
        capacity = 10 if resource_type == "Memory" else 5
        is_my_resource = (i % 2 == 0)
        
        st.session_state.resources_state[resource_name] = {
            "owner": st.session_state.node_id if is_my_resource else "peer",
            "type": resource_type,
            "capacity": capacity,
            "allocated": capacity if is_my_resource else 0,
            "held": is_my_resource
        }

def render_configuration_page():
    """Render configuration page"""
    st.title("🔄 Distributed Deadlock Simulation")
    st.markdown("Configure your network and node parameters")
    
    # Mode selection
    connection_mode = st.radio("🔗 Connection Mode", ["Single Node Pair", "Multiple Nodes"], horizontal=True)
    
    st.markdown("---")
    
    if connection_mode == "Single Node Pair":
        render_two_node_config()
    else:
        render_multi_node_config()

def render_two_node_config():
    """Render two-node configuration"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📌 This Node Configuration")
        node_id = st.text_input("Node ID", value="node1", key="config_node_id")
        my_ip = st.text_input("IP Address", value="127.0.0.1", key="config_my_ip")
        my_port = st.number_input("Port", value=5001, min_value=1024, max_value=65535, key="config_my_port")
        resource = st.text_input("Resource", value="R1", key="config_resource")
    
    with col2:
        st.subheader("👥 Peer Node Configuration")
        peer_ip = st.text_input("Peer IP", value="127.0.0.1", key="config_peer_ip")
        peer_port = st.number_input("Peer Port", value=5002, min_value=1024, max_value=65535, key="config_peer_port")
        
        st.subheader("⚙️ Simulation Parameters")
        num_processes = st.slider("Number of Processes", 2, 50, st.session_state.num_processes, key="config_processes")
        num_resources = st.slider("Number of Resources", 2, 50, st.session_state.num_resources, key="config_resources")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start Simulation", width='stretch'):
            # Validate all inputs
            errors = []
            
            node_valid, node_msg = validate_node_id(node_id)
            if not node_valid:
                errors.append(f"❌ Node ID: {node_msg}")
            
            ip_valid, ip_msg = validate_ip_address(my_ip)
            if not ip_valid:
                errors.append(f"❌ Your IP: {ip_msg}")
            
            port_valid, port_msg = validate_port(my_port)
            if not port_valid:
                errors.append(f"❌ Your Port: {port_msg}")
            
            peer_ip_valid, peer_ip_msg = validate_ip_address(peer_ip)
            if not peer_ip_valid:
                errors.append(f"❌ Peer IP: {peer_ip_msg}")
            
            peer_port_valid, peer_port_msg = validate_port(peer_port)
            if not peer_port_valid:
                errors.append(f"❌ Peer Port: {peer_port_msg}")
            
            res_valid, res_msg = validate_resource_name(resource)
            if not res_valid:
                errors.append(f"❌ Resource: {res_msg}")
            
            if my_port == peer_port and my_ip == peer_ip:
                errors.append("❌ Your port and peer port must be different")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.session_state.node_id = node_id
                st.session_state.my_ip = my_ip
                st.session_state.my_port = my_port
                st.session_state.peer_ip = peer_ip
                st.session_state.peer_port = peer_port
                st.session_state.resource = resource
                st.session_state.num_processes = num_processes
                st.session_state.num_resources = num_resources
                st.session_state.connected_nodes = [
                    {"id": node_id, "ip": my_ip, "port": my_port, "resource": resource},
                    {"id": "peer", "ip": peer_ip, "port": peer_port, "resource": "R2"}
                ]
                initialize_resources()
                init_simulation()
                st.rerun()
    
    with col2:
        st.info("💡 Tip: Use localhost (127.0.0.1) for testing on same machine, or actual IP for network testing")

def render_multi_node_config():
    """Render multi-node configuration"""
    st.subheader("📌 This Node Configuration")
    col1, col2 = st.columns(2)
    with col1:
        node_id = st.text_input("This Node ID", value="node1", key="config_node_id_multi")
        my_ip = st.text_input("This Node IP Address", value="127.0.0.1", key="config_my_ip_multi", 
                              help="Enter your local network IP (e.g., 192.168.x.x for WiFi)")
        my_port = st.number_input("This Node Port", value=5001, min_value=1024, max_value=65535, key="config_my_port_multi")
        resource = st.text_input("My Resource", value="R1", key="config_resource_multi")
    
    with col2:
        st.subheader("⚙️ Simulation Parameters")
        num_processes = st.slider("Number of Processes", 2, 50, st.session_state.num_processes, key="config_processes_multi")
        num_resources = st.slider("Number of Resources", 2, 50, st.session_state.num_resources, key="config_resources_multi")
        num_nodes = st.slider("🖥️ Total Number of Systems to Connect", 2, 50, 3, key="config_nodes_count",
                             help="Include this system + other systems")
    
    st.markdown("---")
    
    # Network Setup Guide
    with st.expander("📡 WiFi Setup Guide - How to Connect Multiple Systems", expanded=False):
        st.markdown("""
        ### Step-by-Step Instructions:
        
        **On Each System:**
        1. **Get Local IP Address:**
           - Windows: Open Command Prompt and type `ipconfig` → Look for "IPv4 Address" (usually 192.168.x.x)
           - Linux/Mac: Open Terminal and type `ifconfig` or `ip addr`
        
        2. **Ensure WiFi Connection:**
           - All systems must be on the same WiFi network
           - Check if systems can ping each other
        
        3. **Configure This App:**
           - Enter your system's IP address (e.g., 192.168.1.100)
           - Choose a unique port (5001, 5002, 5003, etc.)
           - Set the total number of systems
        
        4. **Firewall Settings:**
           - Windows: Allow Python through firewall
           - Linux/Mac: Check iptables/firewall rules
           - Open the ports you specified (e.g., 5001, 5002)
        
        ### Example Setup for 3 Systems:
        ```
        System 1: 192.168.1.100:5001 (node1)
        System 2: 192.168.1.101:5002 (node2)
        System 3: 192.168.1.102:5003 (node3)
        ```
        
        ### Testing Connection:
        - Use `ping` command to verify connectivity
        - Streamlit will show connection status automatically
        """)
    
    st.markdown("---")
    
    # Dynamic peer nodes configuration
    st.subheader(f"👥 Connected Systems Configuration ({num_nodes} total systems)")
    
    peers = []
    
    for i in range(num_nodes - 1):
        with st.expander(f"🖥️ System {i+2}", expanded=(i==0)):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                peer_id = st.text_input(f"Node ID", value=f"node{i+2}", key=f"peer_id_{i}",
                                       help="Unique identifier for this system")
            with col2:
                peer_ip = st.text_input(f"IP Address", value="127.0.0.1", key=f"peer_ip_{i}",
                                       help="Local network IP (192.168.x.x for WiFi)")
            with col3:
                peer_port = st.number_input(f"Port", value=5002+i, min_value=1024, max_value=65535, key=f"peer_port_{i}",
                                           help="Must be unique for each system")
            with col4:
                peer_resource = st.text_input(f"Resource", value=f"R{i+2}", key=f"peer_resource_{i}",
                                             help="Resource managed by this system")
            
            peers.append({
                "id": peer_id,
                "ip": peer_ip,
                "port": peer_port,
                "resource": peer_resource
            })
    
    st.markdown("---")
    
    # Summary before starting
    st.subheader("📋 Configuration Summary")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **Your System:**
        - ID: {node_id}
        - IP: {my_ip}
        - Port: {my_port}
        - Resource: {resource}
        - Total Systems: {num_nodes}
        """)
    
    with col2:
        st.warning(f"""
        **Connected Systems: {len(peers)}**
        
        {"(No other systems configured yet)" if len(peers) == 0 else ""}
        """)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶️ Start Multi-System Simulation", width='stretch'):
            # Validate all inputs
            errors = []
            
            node_valid, node_msg = validate_node_id(node_id)
            if not node_valid:
                errors.append(f"❌ Node ID: {node_msg}")
            
            ip_valid, ip_msg = validate_ip_address(my_ip)
            if not ip_valid:
                errors.append(f"❌ Your IP: {ip_msg}")
            
            port_valid, port_msg = validate_port(my_port)
            if not port_valid:
                errors.append(f"❌ Your Port: {port_msg}")
            
            res_valid, res_msg = validate_resource_name(resource)
            if not res_valid:
                errors.append(f"❌ Resource: {res_msg}")
            
            # Validate peer nodes
            used_ports = {my_port}
            for i, peer in enumerate(peers):
                peer_node_valid, peer_node_msg = validate_node_id(peer['id'])
                if not peer_node_valid:
                    errors.append(f"❌ Peer {i+2} Node ID: {peer_node_msg}")
                
                peer_ip_valid, peer_ip_msg = validate_ip_address(peer['ip'])
                if not peer_ip_valid:
                    errors.append(f"❌ Peer {i+2} IP: {peer_ip_msg}")
                
                peer_port_valid, peer_port_msg = validate_port(peer['port'])
                if not peer_port_valid:
                    errors.append(f"❌ Peer {i+2} Port: {peer_port_msg}")
                
                if peer['port'] in used_ports:
                    errors.append(f"❌ Peer {i+2} Port {peer['port']} already used")
                else:
                    used_ports.add(peer['port'])
                
                peer_res_valid, peer_res_msg = validate_resource_name(peer['resource'])
                if not peer_res_valid:
                    errors.append(f"❌ Peer {i+2} Resource: {peer_res_msg}")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                all_nodes = [{"id": node_id, "ip": my_ip, "port": my_port, "resource": resource}]
                all_nodes.extend(peers)
                
                st.session_state.node_id = node_id
                st.session_state.my_ip = my_ip
                st.session_state.my_port = my_port
                st.session_state.resource = resource
                st.session_state.num_processes = num_processes
                st.session_state.num_resources = num_resources
                st.session_state.connected_nodes = all_nodes
                st.session_state.is_multi_node = True
                
                initialize_resources()
                init_simulation()
                st.rerun()
    
    with col2:
        st.info("💡 Test on localhost first (127.0.0.1) before testing over WiFi")
    
    with col3:
        if st.button("📡 Test Network", width='stretch'):
            st.info("Testing network connectivity to configured systems...")
            for i, peer in enumerate(peers):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex((peer['ip'], peer['port']))
                    sock.close()
                    if result == 0:
                        st.success(f"✅ {peer['id']} ({peer['ip']}:{peer['port']}) - Connected")
                    else:
                        st.warning(f"⚠️ {peer['id']} ({peer['ip']}:{peer['port']}) - Not reachable (system may not be running)")
                except Exception as e:
                    st.error(f"❌ {peer['id']} - Error: {str(e)}")

def check_peer_connection():
    """Check if peer node is reachable"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((st.session_state.peer_ip, st.session_state.peer_port))
        sock.close()
        return result == 0
    except Exception as e:
        return False

def render_connection_status():
    """Render connection status UI"""
    is_connected = check_peer_connection()
    
    st.markdown("---")
    st.subheader("🔗 Connection Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Visual status indicator
        if is_connected:
            st.success("✅ Connected")
            status_color = "#4CAF50"
            status_text = "ONLINE"
        else:
            st.error("❌ Disconnected")
            status_color = "#F44336"
            status_text = "OFFLINE"
        
        # Update session state
        st.session_state.connection_status = status_text
    
    with col2:
        st.markdown(f"**Peer Address:**")
        st.code(f"{st.session_state.peer_ip}:{st.session_state.peer_port}")
    
    with col3:
        st.markdown(f"**This Node:**")
        st.code(f"{st.session_state.my_ip}:{st.session_state.my_port}")
    
    # Connection Details
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Network Information**")
        connection_info = f"""
        - **Status:** {status_text}
        - **This Node ID:** {st.session_state.node_id}
        - **Peer Node ID:** {"node2" if st.session_state.node_id == "node1" else "node1"}
        - **This Node IP:** {st.session_state.my_ip}:{st.session_state.my_port}
        - **Peer Node IP:** {st.session_state.peer_ip}:{st.session_state.peer_port}
        """
        st.info(connection_info)
    
    with col2:
        st.markdown("**Connection Guide**")
        if is_connected:
            st.success("""
            ✅ Peer node is online and reachable
            
            You can now:
            - Request resources from peer
            - Send/receive messages
            - Detect deadlocks
            - Test all deadlock algorithms
            """)
        else:
            st.warning("""
            ⚠️ Peer node is offline
            
            To enable communication:
            1. Start the peer node at:
               `{peer_ip}:{peer_port}`
            2. Ensure both nodes have network connectivity
            3. Check firewall settings
            4. Refresh this page to check status
            """.format(peer_ip=st.session_state.peer_ip, peer_port=st.session_state.peer_port))
    
    # Refresh button
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Refresh Status", width='stretch'):
            st.rerun()
    
    with col2:
        if is_connected:
            st.success("Live connection detected")
        else:
            st.error("No connection available")

def render_detailed_nodes_info():
    """Display detailed information about all nodes"""
    # Get all nodes
    all_nodes = st.session_state.connected_nodes if st.session_state.is_multi_node else [
        {"id": st.session_state.node_id, "ip": st.session_state.my_ip, "port": st.session_state.my_port, "resource": st.session_state.resource},
        {"id": "peer", "ip": st.session_state.peer_ip, "port": st.session_state.peer_port, "resource": "R2"}
    ]
    
    # Display each node with detailed info
    cols = st.columns(min(3, len(all_nodes)))
    
    for idx, node in enumerate(all_nodes):
        with cols[idx % len(cols)]:
            is_current = node['id'] == st.session_state.node_id
            
            if is_current:
                with st.container(border=True):
                    st.markdown(f"### 🟢 {node['id']} (Current Node)")
                    st.info(f"""
                    **Status:** Active
                    
                    **Network Details:**
                    - IP Address: `{node['ip']}`
                    - Port: `{node['port']}`
                    - Resource: `{node['resource']}`
                    
                    **Configuration:**
                    - Mode: {st.session_state.mode.upper()}
                    - Uptime: Running
                    """)
            else:
                with st.container(border=True):
                    st.markdown(f"### 🟠 {node['id']} (Remote Node)")
                    
                    # Check connection status
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(1)
                        result = sock.connect_ex((node['ip'], node['port']))
                        sock.close()
                        is_online = result == 0
                    except:
                        is_online = False
                    
                    status_badge = "✅ Online" if is_online else "❌ Offline"
                    status_color = "🟢" if is_online else "🔴"
                    
                    if is_online:
                        st.success(f"{status_color} {status_badge}")
                    else:
                        st.error(f"{status_color} {status_badge}")
                    
                    st.info(f"""
                    **Network Details:**
                    - IP Address: `{node['ip']}`
                    - Port: `{node['port']}`
                    - Resource: `{node['resource']}`
                    
                    **Status:**
                    - Connectivity: {status_badge}
                    """)

def render_connected_nodes_display():
    """Display all connected nodes in the network"""
    if not st.session_state.connected_nodes:
        return
    
    st.subheader("🌐 Network Topology")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Connected Systems**")
        st.metric("Total Nodes", len(st.session_state.connected_nodes))
        st.write("---")
        for i, node in enumerate(st.session_state.connected_nodes, 1):
            node_name = node['id']
            if node['id'] == st.session_state.node_id:
                st.success(f"✅ {i}. {node_name} (You)")
            else:
                st.info(f"  {i}. {node_name}")
    
    with col2:
        st.markdown("**Network Addresses**")
        st.write("---")
        for node in st.session_state.connected_nodes:
            connection_status = "🟢" if node['id'] == st.session_state.node_id else "❓"
            st.code(f"{connection_status} {node['ip']}:{node['port']}")
    
    with col3:
        st.markdown("**Resources**")
        st.write("---")
        for node in st.session_state.connected_nodes:
            status = "🔒" if node['id'] == st.session_state.node_id else "📦"
            st.write(f"{status} {node['resource']}")
    
    st.markdown("---")
    
    # Network visualization as table
    st.markdown("**📋 Complete Network Configuration**")
    nodes_data = pd.DataFrame([
        {
            "System": "📍 " + node['id'] + (" (You)" if node['id'] == st.session_state.node_id else ""),
            "IP Address": node['ip'],
            "Port": node['port'],
            "Resource": node['resource']
        }
        for node in st.session_state.connected_nodes
    ])
    st.dataframe(nodes_data, width='stretch')

def render_simulation_page():
    """Render main simulation page - all elements on single page"""
    st.title(f"🛜Distributed Deadlock Simulation - {st.session_state.node_id}")
    
    st.sidebar.subheader("🎛 Controls")
    is_connected = check_peer_connection()
    connection_badge = "🟢 Online" if is_connected else "🔴 Offline"

    st.sidebar.metric("📡 Peer Status:", connection_badge)

    # ───────── Resource Operations ─────────
    st.sidebar.markdown("**Resource Operations**")

    if st.sidebar.button("📤 Request Resource", use_container_width=True):
        st.session_state.stats["requests"] += 1
        log_message("━━━━━ REQUEST INITIATED ━━━━━")
        log_message(f"Target: {st.session_state.resource}")
        log_message(f"Mode: {st.session_state.mode.upper()}")
        st.success("Resource request sent!")

    if st.sidebar.button("📥 Release Resource", use_container_width=True):
        st.session_state.stats["releases"] += 1
        log_message("━━━━━ RELEASE INITIATED ━━━━━")
        log_message(f"Releasing: {st.session_state.resource}")
        st.success("Resource released!")

    if st.sidebar.button("🔙 Back", use_container_width=True):
        st.session_state.simulation_started = False
        st.session_state.logs = []
        st.rerun()

    st.sidebar.markdown("---")

    # ───────── Auto-Pilot ─────────
    st.sidebar.markdown("**Auto-Pilot**")

    if st.sidebar.button("🔄 Start Auto", use_container_width=True, key="start_auto"):
        st.session_state.auto_pilot = not st.session_state.auto_pilot
        status = "STARTED" if st.session_state.auto_pilot else "STOPPED"
        log_message(f"Auto-pilot {status}")
        st.rerun()

    interval = st.sidebar.slider("Interval(s):", 1.0, 10.0, 2.0)

    st.sidebar.markdown("---")

    # ───────── Simulation ─────────
    st.sidebar.markdown("**Simulation**")

    if st.sidebar.button("⏸ Pause", use_container_width=True, key="pause"):
        st.session_state.paused = not st.session_state.paused
        status = "PAUSED" if st.session_state.paused else "RESUMED"
        log_message(f"Simulation {status}")
        st.rerun()

    if st.sidebar.button("🚀 Step", use_container_width=True):
        log_message("Executing one simulation step")

    st.sidebar.markdown("---")

    # ───────── Deadlock Mode ─────────
    st.sidebar.markdown("**Deadlock Mode**")

    new_mode = st.sidebar.radio(
        "Mode",
        ["Detection", "Prevention", "Avoidance"],
        horizontal=False,
        label_visibility="visible"
    )

    mode_lower = new_mode.lower()
    if mode_lower != st.session_state.mode:
        st.session_state.mode = mode_lower
        log_message(f"Switched to {mode_lower.upper()} mode")
        st.rerun()
    
    st.markdown("---")
    
    # Connection Status Banner at Top
    st.subheader("🔗 Resource Allocation Graph")

    # User-adjustable size controls
    st.markdown("### 📐 Graph Size Controls")
    col_w, col_h = st.columns(2)

    with col_w:
        graph_width = st.slider("Width (px)", 400, 1600, 900)
    with col_h:
        graph_height = st.slider("Height (px)", 300, 1200, 600)

    # Render graph with chosen size
    fig_graph = create_node_graph_visualization()
    fig_graph.update_layout(width=graph_width, height=graph_height)

    st.plotly_chart(fig_graph, config={"responsive": False})

    st.subheader("📊 Statistics")
    cols = st.columns(7)
    cols[0].metric("📤 Requests", st.session_state.stats["requests"])
    cols[1].metric("✅ Grants", st.session_state.stats["grants"])
    cols[2].metric("❌ Denials", st.session_state.stats["denials"])
    cols[3].metric("⚠️ Deadlocks", st.session_state.stats["deadlocks"])
    cols[4].metric("🔄 Recoveries", st.session_state.stats["recoveries"])
    cols[5].metric("🛡️ Prevented", st.session_state.stats["preventions"])
    cols[6].metric("🎯 Avoided", st.session_state.stats["avoidances"])
    
    # Statistics Display
    st.subheader("📊 Full Statistics")
    stats_text = f"Requests: {st.session_state.stats['requests']} | Grants: {st.session_state.stats['grants']} | Denials: {st.session_state.stats['denials']} | Deadlocks: {st.session_state.stats['deadlocks']} | Recoveries: {st.session_state.stats['recoveries']} | Prevented: {st.session_state.stats['preventions']} | Avoided: {st.session_state.stats['avoidances']}"
    st.info(stats_text)
    
    st.markdown("---")
    
    # Resource Pool Status
    st.subheader("📦 Resource Pool Status")
    col_res1, col_res2 = st.columns(2)
    
    with col_res1:
        st.markdown("**Allocation Status**")
        if st.session_state.resources_state:
            for name, info in st.session_state.resources_state.items():
                allocated = info["allocated"]
                capacity = info["capacity"]
                percentage = (allocated / capacity) * 100 if capacity > 0 else 0
                st.progress(percentage / 100, text=f"{name} ({info['type']}): {allocated}/{capacity}")
    
    with col_res2:
        st.markdown("**Resources by Type**")
        if st.session_state.resources_state:
            type_data = {}
            for name, info in st.session_state.resources_state.items():
                res_type = info["type"]
                if res_type not in type_data:
                    type_data[res_type] = {"total": 0, "allocated": 0}
                type_data[res_type]["total"] += info["capacity"]
                type_data[res_type]["allocated"] += info["allocated"]
            
            for res_type, data in type_data.items():
                available = data["total"] - data["allocated"]
                st.write(f"**{res_type}:** {data['allocated']}/{data['total']} (Available: {available})")
    
    st.markdown("---")
    
    # Current Mode Info
    st.subheader("ℹ️ Current Mode Info")
    mode_descriptions = {
        "detection": "Detection Mode: Monitors for circular wait conditions and detects deadlocks using probe messages.",
        "prevention": "Prevention Mode: Uses resource ordering and wait-die protocol to prevent deadlocks from occurring.",
        "avoidance": "Avoidance Mode: Uses Banker's Algorithm to ensure the system stays in a safe state."
    }
    st.success(mode_descriptions.get(st.session_state.mode, "Unknown mode"))
    
    st.markdown("---")
    
    # Loaded Modules
    st.subheader("✅ Loaded Algorithm Modules")
    modules_text = """
    • coordinator.py - Main coordination and system state
    • detection.py - Deadlock Detection (DFS cycle detection)
    • prevention.py - Deadlock Prevention (Resource ordering)
    • banker.py - Deadlock Avoidance (Banker's Algorithm)
    • process.py - Process management and state tracking
    • resource.py - Resource allocation and tracking
    """
    st.info(modules_text)
    
    st.markdown("---")
    
    # Activity Log
    st.subheader("📋 Activity Log")
    col_log1, col_log2, col_log3 = st.columns(3)
    
    with col_log1:
        if st.button("🗑️ Clear Log", width='stretch'):
            st.session_state.logs = []
            st.rerun()
    
    with col_log2:
        if st.button("💾 Export Log", width='stretch'):
            log_content = "\n".join(st.session_state.logs)
            st.download_button(
                label="📥 Download",
                data=log_content,
                file_name=f"simulation_log_{st.session_state.node_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                width='stretch'
            )
    
    with col_log3:
        st.write("")  # Placeholder for alignment
    
    # Display logs
    log_container = st.container()
    with log_container:
        log_text = "\n".join(st.session_state.logs[-50:])  # Show last 50 logs
        st.text_area("Log Output:", value=log_text, height=200, disabled=True)
    
    st.markdown("---")
    
    # Connection Status Section
    render_connection_status()
    
    st.markdown("---")
    
    # Connected Nodes Display
    if st.session_state.is_multi_node and st.session_state.connected_nodes:
        st.subheader("🌐 Connected Nodes Network")
        render_connected_nodes_display()
        st.markdown("---")
    
    # Detailed Nodes Information Panel
    st.subheader("📊 Detailed Node Information")
    render_detailed_nodes_info()

def create_node_graph_visualization():
    """Create a network graph visualization showing all nodes and resources"""
    # Create figure
    fig = go.Figure()
    
    # Get all connected nodes
    all_nodes = st.session_state.connected_nodes if st.session_state.is_multi_node else [
        {"id": st.session_state.node_id, "ip": st.session_state.my_ip, "port": st.session_state.my_port, "resource": st.session_state.resource},
        {"id": "peer", "ip": st.session_state.peer_ip, "port": st.session_state.peer_port, "resource": "R2"}
    ]
    
    # Calculate positions for all nodes in a circle
    num_nodes = len(all_nodes)
    node_radius = 2
    node_positions = {}
    
    for i, node in enumerate(all_nodes):
        angle = (2 * np.pi * i) / num_nodes
        x = node_radius * np.cos(angle)
        y = node_radius * np.sin(angle)
        node_positions[node['id']] = (x, y)
    
    # Extract node data
    node_ids = [node['id'] for node in all_nodes]
    node_x = [node_positions[nid][0] for nid in node_ids]
    node_y = [node_positions[nid][1] for nid in node_ids]
    
    # Determine node colors
    node_colors = []
    for node in all_nodes:
        if node['id'] == st.session_state.node_id:
            node_colors.append("#2196F3")  # Blue for current node
        elif node['id'] in st.session_state.deadlock_cycle:
            node_colors.append("#FF5252")  # Red for deadlock
        else:
            node_colors.append("#FF9800")  # Orange for other nodes
    
    # Create hover text for nodes
    node_hover_text = []
    for node in all_nodes:
        status = "🟢 You" if node['id'] == st.session_state.node_id else "🟠 Peer"
        hover = f"<b>{node['id']}</b><br>" \
                f"Status: {status}<br>" \
                f"IP: {node['ip']}<br>" \
                f"Port: {node['port']}<br>" \
                f"Resource: {node['resource']}"
        node_hover_text.append(hover)
    
    # Add nodes to graph
    fig.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        marker=dict(size=100, color=node_colors, line=dict(width=2, color='white')),
        text=node_ids,
        textposition="middle center",
        textfont=dict(size=12, color="white", family="Arial Black"),
        hovertext=node_hover_text,
        hovertemplate='%{hovertext}<extra></extra>',
        name="Nodes",
        showlegend=True
    ))
    
    # Add resource nodes around each system node
    resources = list(st.session_state.resources_state.keys())
    resource_trace_x = []
    resource_trace_y = []
    resource_colors = []
    resource_labels = []
    resource_hover = []
    
    for res_idx, res in enumerate(resources):
        res_info = st.session_state.resources_state[res]
        
        # Find which node owns this resource
        owner_node = None
        for node in all_nodes:
            if node['resource'] == res or (res_idx % len(all_nodes) == all_nodes.index(node)):
                owner_node = node
                break
        
        if owner_node is None:
            owner_node = all_nodes[res_idx % len(all_nodes)]
        
        # Position resources around their owner node
        owner_x, owner_y = node_positions[owner_node['id']]
        
        # Create offset for resource position (around the node)
        offset_angle = (2 * np.pi * (res_idx % 3)) / 3
        offset_dist = 0.6
        res_x = owner_x + offset_dist * np.cos(offset_angle)
        res_y = owner_y + offset_dist * np.sin(offset_angle)
        
        resource_trace_x.append(res_x)
        resource_trace_y.append(res_y)
        resource_colors.append("#4CAF50" if res_info["owner"] == st.session_state.node_id else "#81C784")
        resource_labels.append(res)
        
        resource_hover.append(
            f"<b>{res}</b><br>"
            f"Type: {res_info['type']}<br>"
            f"Owner: {res_info['owner']}<br>"
            f"Allocation: {res_info['allocated']}/{res_info['capacity']}<br>"
            f"Status: {'Held' if res_info['held'] else 'Free'}"
        )
    
    # Add resource nodes
    if resource_trace_x:
        fig.add_trace(go.Scatter(
            x=resource_trace_x,
            y=resource_trace_y,
            mode='markers+text',
            marker=dict(size=60, color=resource_colors, symbol="square", line=dict(width=1, color='white')),
            text=resource_labels,
            textposition="middle center",
            textfont=dict(size=10, color="white", family="Arial"),
            hovertext=resource_hover,
            hovertemplate='%{hovertext}<extra></extra>',
            name="Resources",
            showlegend=True
        ))
    
    # Add connections from resources to nodes (holds relationship)
    for idx, res in enumerate(resources):
        res_info = st.session_state.resources_state[res]
        
        # Find owner node
        owner_node = None
        for node in all_nodes:
            if node['resource'] == res or (idx % len(all_nodes) == all_nodes.index(node)):
                owner_node = node
                break
        if owner_node is None:
            owner_node = all_nodes[idx % len(all_nodes)]
        
        owner_x, owner_y = node_positions[owner_node['id']]
        res_x = resource_trace_x[idx] if idx < len(resource_trace_x) else owner_x
        res_y = resource_trace_y[idx] if idx < len(resource_trace_y) else owner_y
        
        fig.add_trace(go.Scatter(
            x=[res_x, owner_x],
            y=[res_y, owner_y],
            mode='lines',
            line=dict(color="#4CAF50" if res_info["owner"] == st.session_state.node_id else "#81C784", width=2),
            hovertemplate='Holds<extra></extra>',
            showlegend=False,
            name="Holds"
        ))
    
    # Draw waiting connection if applicable
    if st.session_state.waiting_for and st.session_state.waiting_for in resources:
        waiting_idx = resources.index(st.session_state.waiting_for)
        waiting_x = resource_trace_x[waiting_idx] if waiting_idx < len(resource_trace_x) else 0
        waiting_y = resource_trace_y[waiting_idx] if waiting_idx < len(resource_trace_y) else 0
        current_x, current_y = node_positions[st.session_state.node_id]
        
        fig.add_trace(go.Scatter(
            x=[current_x, waiting_x],
            y=[current_y, waiting_y],
            mode='lines',
            line=dict(color="#FF1744", width=3, dash="dash"),
            hovertemplate='Waits For<extra></extra>',
            showlegend=False,
            name="Waits For"
        ))
    
    # Update layout
    fig.update_layout(
        title=f"Network Topology - {len(all_nodes)} Nodes, {len(resources)} Resources",
        showlegend=True,
        hovermode='closest',
        margin=dict(b=20, l=20, r=20, t=50),
        xaxis=dict(showgrid=True, zeroline=False, showticklabels=False, gridcolor='#e0e0e0'),
        yaxis=dict(showgrid=True, zeroline=False, showticklabels=False, gridcolor='#e0e0e0'),
        plot_bgcolor='#ffffff',
        paper_bgcolor='#f8f9fa',
        height=600,
        font=dict(family="Arial", size=12),
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)')
    )
    
    return fig

def render_dashboard():
    """Render dashboard with statistics and visualization"""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📤 Requests", st.session_state.stats["requests"])
    with col2:
        st.metric("✅ Grants", st.session_state.stats["grants"])
    with col3:
        st.metric("❌ Denials", st.session_state.stats["denials"])
    with col4:
        st.metric("⚠️ Deadlocks", st.session_state.stats["deadlocks"])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔄 Recoveries", st.session_state.stats["recoveries"])
    with col2:
        st.metric("🛡️ Prevented", st.session_state.stats["preventions"])
    with col3:
        st.metric("🎯 Avoided", st.session_state.stats["avoidances"])
    with col4:
        st.metric("📤 Releases", st.session_state.stats["releases"])
    
    st.markdown("---")
    
    # Node Visualization
    st.subheader("🔗 Resource Allocation Graph")
    fig_graph = create_node_graph_visualization()
    st.plotly_chart(fig_graph, width='stretch')
    
    st.markdown("---")
    
    # Create visualization
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Statistics Over Time")
        stats_data = pd.DataFrame({
            "Category": ["Requests", "Grants", "Denials", "Deadlocks"],
            "Count": [
                st.session_state.stats["requests"],
                st.session_state.stats["grants"],
                st.session_state.stats["denials"],
                st.session_state.stats["deadlocks"]
            ]
        })
        fig = px.bar(stats_data, x="Category", y="Count", color="Category")
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        st.subheader("🎯 Prevention & Avoidance")
        prevention_data = pd.DataFrame({
            "Method": ["Prevention", "Avoidance", "Detection"],
            "Count": [
                st.session_state.stats["preventions"],
                st.session_state.stats["avoidances"],
                st.session_state.stats["deadlocks"]
            ]
        })
        fig = px.pie(prevention_data, values="Count", names="Method")
        st.plotly_chart(fig, width='stretch')


def main():
    """Main application"""
    if not st.session_state.simulation_started:
        render_configuration_page()
    else:
        render_simulation_page()

if __name__ == "__main__":
    main()
