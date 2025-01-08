import threading

class Registry:
    def __init__(self):
        self.connected_peers:dict[str, dict[str,str]] = {}
        # Connected peers is in the following format:
            # {
            #     "peer_id": {
            #         "ip": "
            #         "port": "
            #         "relay": True/False
            #     }

        self.ip_to_peer_id:dict[str, str] = {}

        self.relay_peers:list[str] = []
        self.registry_mutex = threading.Lock()

    def add_peer(self, peer_id:str, ip:str, port:str):
        """
        Add a peer to the registry
        
        Args:
            peer_id (str): The peer's id
            ip (str): The peer's ip
            port (str): The peer's port
            
        """
        with self.registry_mutex:

            self.connected_peers[peer_id] = {
                "ip": ip,
                "port": port,
                "relay": False
            }
            self.ip_to_peer_id[ip] = peer_id

    def remove_peer(self, peer_id:str):
        """
        Remove a peer from the registry

        Args:
            peer_id (str): The peer's id
        """
        with self.registry_mutex:
            if self.connected_peers[peer_id]["relay"]:
                self.relay_peers.remove(peer_id)
            self.connected_peers.pop(peer_id)
            self.ip_to_peer_id.pop(self.connected_peers[peer_id]["ip"])
    
    def get_peer(self, peer_id:str):
        return self.connected_peers.get(peer_id, None)
    
    def get_peer_by_ip(self, ip:str):
        return self.connected_peers.get(self.ip_to_peer_id.get(ip), None)
    
    def get_all_peers(self):
        return self.connected_peers
    
    def get_relay_peers(self):
        """
        Get all relay peers
        
        Returns:
            list: A list of relay peers
        """
        return self.relay_peers
        
    def add_relay_peer(self, peer_id:str, ip:str, port:str):
        """
        Add a relay peer to the registry
        
        Args:
            peer_id (str): The peer's id
            ip (str): The peer's ip
            port (str): The peer's port
        """
        with self.registry_mutex:
            if peer_id not in self.connected_peers:
                self.connected_peers[peer_id] = {
                    "ip": ip,
                    "port": port,
                    "relay": True
                }
                self.ip_to_peer_id[ip] = peer_id
            else:
                self.connected_peers[peer_id]["relay"] = True

            self.relay_peers.append(peer_id)