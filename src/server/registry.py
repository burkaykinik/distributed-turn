import threading
from typing import Dict, Tuple, Optional

class Registry:
    def __init__(self):
        # peer_id -> { "addr": (ip, port), "is_relay": bool }
        self.peers: Dict[str, Dict] = {}

        # session_id -> {
        #    "peer_a": str,
        #    "peer_b": str,
        #    "relay": str,      # relay's peer_id
        #    "status": str,
        #    "ports": {         # optional: track the assigned ports
        #       "peer_a": int,
        #       "peer_b": int
        #    }
        # }
        self.active_sessions: Dict[str, Dict] = {}

        # session_id -> {
        #   "from_peer": str,
        #   "to_peer": str,
        #   "status": "pending"
        # }
        self.pending_connections: Dict[str, Dict] = {}

        self.mutex = threading.Lock()

    def register_peer(self, peer_id: str, addr: Tuple[str, int], is_relay: bool = False) -> bool:
        """Register a new peer or update existing peer's information."""
        with self.mutex:
            self.peers[peer_id] = {
                "addr": addr,
                "is_relay": is_relay
            }
            return True

    def get_peer_addr(self, peer_id: str) -> Optional[Tuple[str, int]]:
        """Get a peer's address."""
        with self.mutex:
            peer = self.peers.get(peer_id)
            return peer["addr"] if peer else None

    def is_peer_relay(self, peer_id: str) -> bool:
        """Check if a peer is relay-capable."""
        with self.mutex:
            peer = self.peers.get(peer_id)
            return peer["is_relay"] if peer else False

    def get_peer_id_by_addr(self, addr: Tuple[str, int]) -> Optional[str]:
        """Get peer ID from its address."""
        with self.mutex:
            for pid, pdata in self.peers.items():
                if pdata["addr"] == addr:
                    return pid
        return None

    def get_available_relays(self) -> list:
        """Get a list of available relay peers."""
        with self.mutex:
            # You might add logic to filter out busy relays or select one behind full-cone NAT, etc.
            return [peer_id for peer_id, data in self.peers.items() if data["is_relay"]]

    def create_pending_connection(self, session_id: str, from_peer: str, to_peer: str) -> bool:
        """Create a pending connection between two peers."""
        with self.mutex:
            self.pending_connections[session_id] = {
                "from_peer": from_peer,
                "to_peer": to_peer,
                "status": "pending"
            }
            return True

    def get_pending_connection(self, from_peer: str, to_peer: str) -> Optional[Dict]:
        """Get a pending connection by from_peer and to_peer."""
        with self.mutex:
            for sid, conn in self.pending_connections.items():
                if conn["from_peer"] == from_peer and conn["to_peer"] == to_peer:
                    return {"session_id": sid, **conn}
            return None

    def create_session(self, session_id: str, peer_a: str, peer_b: str, relay: str) -> bool:
        """Create a new relay session."""
        with self.mutex:
            if session_id in self.pending_connections:
                del self.pending_connections[session_id]

            self.active_sessions[session_id] = {
                "peer_a": peer_a,
                "peer_b": peer_b,
                "relay": relay,
                "status": "active",
                "ports": {}
            }
            return True

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session information."""
        with self.mutex:
            return self.active_sessions.get(session_id)

    def update_session_ports(self, session_id: str, ports: Dict[str, int]) -> bool:
        """
        Store the relay's allocated ports in the session.
        `ports` might be {peer_a_id: 12345, peer_b_id: 23456}, for example.
        """
        with self.mutex:
            session = self.active_sessions.get(session_id)
            if not session:
                return False
            session["ports"] = ports
            return True
