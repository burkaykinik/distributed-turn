import socket
import json

class CentralServer:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.peers = {}            # {peer_id: (ip, port)}
        self.relay_candidates = {} # {peer_id: (ip, port)}
        print(f"\n[SERVER] Starting on {host}:{port}")
        
    def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        print(f"[SERVER] Ready to handle connections")
        
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                message = json.loads(data.decode())
                print(f"\n[SERVER] Received: {message} from {addr}")
                
                message_type = message.get("type", "")
                
                if message_type == "register":
                    self._handle_register(sock, message, addr)
                elif message_type == "connect_request":
                    self._handle_connect_request(sock, message, addr)
                
            except Exception as e:
                print(f"[SERVER] Error: {e}")
    
    def _handle_register(self, sock, message, addr):
        peer_id = message["peer_id"]
        is_relay_capable = message.get("is_relay_capable", False)
        
        self.peers[peer_id] = addr
        if is_relay_capable:
            self.relay_candidates[peer_id] = addr
            print(f"[SERVER] Registered relay-capable peer: {peer_id}")
        else:
            print(f"[SERVER] Registered regular peer: {peer_id}")
            
        print(f"[SERVER] Current peers: {list(self.peers.keys())}")
        print(f"[SERVER] Available relays: {list(self.relay_candidates.keys())}")
            
        response = {
            "type": "register_response",
            "status": "success"
        }
        sock.sendto(json.dumps(response).encode(), addr)
    
    def _handle_connect_request(self, sock, message, addr):
        peer_a_id = message["from_peer"]
        peer_b_id = message["to_peer"]
        
        print(f"\n[SERVER] Connection request: {peer_a_id} -> {peer_b_id}")
        
        if peer_b_id not in self.peers:
            print(f"[SERVER] Error: Target peer {peer_b_id} not found")
            response = {"type": "error", "message": "Peer not found"}
            sock.sendto(json.dumps(response).encode(), addr)
            return
            
        # Select first available relay
        if not self.relay_candidates:
            print(f"[SERVER] Error: No relay nodes available")
            response = {"type": "error", "message": "No relay nodes available"}
            sock.sendto(json.dumps(response).encode(), addr)
            return
            
        relay_id, relay_addr = next(iter(self.relay_candidates.items()))
        print(f"[SERVER] Selected relay: {relay_id}")
        
        # Notify peer B
        notify_b = {
            "type": "incoming_connection",
            "from_peer": peer_a_id,
            "relay_id": relay_id,
            "relay_addr": relay_addr
        }
        print(f"[SERVER] Notifying peer B ({peer_b_id})")
        sock.sendto(json.dumps(notify_b).encode(), self.peers[peer_b_id])
        
        # Send relay info to peer A
        response = {
            "type": "connect_response",
            "relay_id": relay_id,
            "relay_addr": relay_addr,
            "peer_b_id": peer_b_id
        }
        print(f"[SERVER] Sending relay info to peer A ({peer_a_id})")
        sock.sendto(json.dumps(response).encode(), addr)

if __name__ == "__main__":
    server = CentralServer()
    server.start()