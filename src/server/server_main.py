import socket
import json
import threading
import uuid
from typing import Dict, Tuple
from .registry import Registry

class Server:
    def __init__(self, host: str = "0.0.0.0", port: int = 50000):
        self.host = host
        self.port = port
        self.registry = Registry()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False

    def start(self):
        """Start the server"""
        self.sock.bind((self.host, self.port))
        self.running = True
        print(f"[SERVER] Started on {self.host}:{self.port}")

        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                message = json.loads(data.decode())
                self._handle_message(message, addr)
            except Exception as e:
                print(f"[SERVER] Error handling message: {e}")

    def _handle_message(self, message: Dict, addr: Tuple[str, int]):
        """Handle incoming messages"""
        msg_type = message.get("type")
        print(f"[SERVER] Received {msg_type} from {addr}")
        
        if msg_type == "register":
            self._handle_register(message, addr)

        elif msg_type == "connect_request":
            self._handle_connect_request(message, addr)

        elif msg_type == "relay_ready":
            self._handle_relay_ready(message, addr)

        elif msg_type == "accept_connection":
            self._handle_accept_connection(message, addr)

        else:
            print(f"[SERVER] Unknown message type: {msg_type}")

    def _handle_register(self, message: Dict, addr: Tuple[str, int]):
        """Handle peer registration"""
        peer_id = message["peer_id"]
        is_relay = message.get("is_relay_capable", False)
        
        self.registry.register_peer(peer_id, addr, is_relay)
        print(f"[SERVER] Registered {'relay' if is_relay else 'peer'}: {peer_id}")

        response = {
            "type": "register_response",
            "status": "success"
        }
        self.sock.sendto(json.dumps(response).encode(), addr)

    def _handle_connect_request(self, message: Dict, addr: Tuple[str, int]):
        """Handle connection request between peers"""
        from_peer = message["from_peer"]
        to_peer = message["to_peer"]
        
        print(f"[SERVER] Connection request: {from_peer} -> {to_peer}")

        # Verify peers exist
        to_peer_addr = self.registry.get_peer_addr(to_peer)
        if not to_peer_addr:
            self._send_error(addr, "Target peer not found")
            return

        # Notify Peer B about incoming connection
        notify_msg = {
            "type": "incoming_connection",
            "from_peer": from_peer
        }
        self.sock.sendto(json.dumps(notify_msg).encode(), to_peer_addr)
        print(f"[SERVER] Notified peer {to_peer} about incoming connection")

        # Create session ID to track this connection request
        session_id = str(uuid.uuid4())
        
        # Store pending connection in registry
        self.registry.create_pending_connection(session_id, from_peer, to_peer)
        
        print(f"[SERVER] Created pending connection with session {session_id}")

    def _handle_accept_connection(self, message: Dict, addr: Tuple[str, int]):
        """Handle connection acceptance from Peer B"""
        from_peer = message["from_peer"]
        accepting_peer_id = self.registry.get_peer_id_by_addr(addr)
        
        print(f"[SERVER] Peer {accepting_peer_id} accepted connection from {from_peer}")
        
        # Find pending connection
        pending_conn = self.registry.get_pending_connection(from_peer, accepting_peer_id)
        if not pending_conn:
            print(f"[SERVER] No pending connection found")
            return

        # Choose the first available relay (simple approach)
        available_relays = self.registry.get_available_relays()
        if not available_relays:
            self._send_error(addr, "No relay peers available")
            return

        relay_peer = available_relays[0]
        relay_addr = self.registry.get_peer_addr(relay_peer)
        session_id = pending_conn["session_id"]

        # Create active session in registry
        self.registry.create_session(session_id, from_peer, accepting_peer_id, relay_peer)

        # Send relay setup request to the chosen relay
        relay_setup = {
            "type": "relay_setup",
            "session_id": session_id,
            "peer_a": from_peer,
            "peer_b": accepting_peer_id
        }
        print(f"[SERVER] Sending relay setup to {relay_peer} at {relay_addr}")
        self.sock.sendto(json.dumps(relay_setup).encode(), relay_addr)

    def _handle_relay_ready(self, message: Dict, addr: Tuple[str, int]):
        """Handle relay ready notification from the relay peer"""
        session_id = message["session_id"]
        session = self.registry.get_session(session_id)
        if not session:
            print(f"[SERVER] No session found for {session_id}")
            return

        relay_ports = message["ports"]
        print(f"[SERVER] Relay {session['relay']} ready with ports: {relay_ports}")

        # Notify peers of relay details
        for peer_id in [session["peer_a"], session["peer_b"]]:
            peer_addr = self.registry.get_peer_addr(peer_id)
            if peer_addr:
                relay_info = {
                    "type": "relay_info",
                    "session_id": session_id,
                    "relay_addr": addr,  # relay's (IP, port) from the server's perspective
                    "port": relay_ports[peer_id]  # the specific port for this peer
                }
                print(f"[SERVER] Sending relay info to {peer_id}: {relay_info}")
                self.sock.sendto(json.dumps(relay_info).encode(), peer_addr)

    def _send_error(self, addr: Tuple[str, int], message: str):
        """Send error message to peer"""
        error = {
            "type": "error",
            "message": message
        }
        self.sock.sendto(json.dumps(error).encode(), addr)

if __name__ == "__main__":
    server = Server()
    server.start()
