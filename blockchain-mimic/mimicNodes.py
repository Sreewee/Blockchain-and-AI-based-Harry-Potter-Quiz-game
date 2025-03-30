import flask
from flask import Flask, request, jsonify
import socket
from zeroconf import ServiceInfo, Zeroconf
import threading
import time
import requests
import uuid
import logging
from flask_sqlalchemy import SQLAlchemy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('p2p-flask')

app = Flask(__name__)
db_port = app.run_port
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///Databse/db{db_port}.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

peers = {}
my_uuid = str(uuid.uuid4())
my_info = {
    "uuid": my_uuid,
    "name": socket.gethostname(),
    "timestamp": time.time()
}

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def register_service(port):
    local_ip = get_local_ip()
    service_name = f"p2pflask-{my_uuid}._http._tcp.local."
    service_info = ServiceInfo(
        "_http._tcp.local.",
        service_name,
        addresses=[socket.inet_aton(local_ip)],
        port=port,
        properties={"uuid": my_uuid, "name": socket.gethostname()}
    )
    zeroconf = Zeroconf()
    zeroconf.register_service(service_info)
    logger.info(f"Registered service on {local_ip}:{port} with name: {service_name}")
    return zeroconf, service_info

class ServiceListener:
    def __init__(self):
        self.zeroconf = Zeroconf()
        
    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            address = socket.inet_ntoa(info.addresses[0])
            port = info.port
            uuid_value = info.properties.get(b'uuid', b'').decode('utf-8')
            if uuid_value == my_uuid:
                return
            peer_url = f"http://{address}:{port}"
            peers[uuid_value] = {
                "url": peer_url,
                "last_seen": time.time(),
                "name": info.properties.get(b'name', b'').decode('utf-8')
            }
            logger.info(f"Discovered peer: {peer_url}")
            try:
                requests.post(f"{peer_url}/peer", json=my_info, timeout=2)
            except requests.RequestException as e:
                logger.warning(f"Failed to contact newly discovered peer: {e}")
    
    def remove_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            uuid_value = info.properties.get(b'uuid', b'').decode('utf-8')
            if uuid_value in peers:
                logger.info(f"Peer {peers[uuid_value]['url']} has left the network")
                del peers[uuid_value]
    
    def update_service(self, zc, type_, name):
        pass
        
    def start_discovery(self):
        browser = self.zeroconf.add_service_listener("_http._tcp.local.", self)
        logger.info("Started service discovery")
        return browser

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "uuid": my_uuid,
        "name": socket.gethostname(),
        "peers": len(peers)
    })

@app.route('/peers')
def get_peers():
    return jsonify({
        "uuid": my_uuid,
        "name": socket.gethostname(),
        "peers": peers
    })

@app.route('/peer', methods=['POST'])
def register_peer():
    peer_info = request.json
    peer_uuid = peer_info.get('uuid')
    if peer_uuid == my_uuid:
        return jsonify({"status": "ignored", "reason": "self-reference"})
    if peer_uuid in peers:
        peers[peer_uuid]["last_seen"] = time.time()
        logger.info(f"Updated existing peer: {peer_uuid}")
    else:
        try:
            peer_url = f"http://{request.remote_addr}:{request.environ.get('REMOTE_PORT', 5000)}"
            peers[peer_uuid] = {
                "url": peer_url,
                "name": peer_info.get('name', 'Unknown'),
                "last_seen": time.time()
            }
            logger.info(f"Registered new peer via direct contact: {peer_url}")
        except Exception as e:
            logger.error(f"Failed to process peer registration: {e}")
    return jsonify(my_info)

@app.route('/message', methods=['POST'])
def receive_message():
    message = request.json
    sender = message.get('sender', 'Unknown')
    content = message.get('content', '')
    logger.info(f"Message from {sender}: {content}")

def maintenance_task():
    while True:
        current_time = time.time()
        stale_peers = [uuid for uuid, info in peers.items() 
                      if current_time - info['last_seen'] > 300]
        for uuid in stale_peers:
            logger.info(f"Removing stale peer: {peers[uuid]['url']}")
            del peers[uuid]
        for uuid, info in list(peers.items()):
            try:
                response = requests.post(f"{info['url']}/peer", json=my_info, timeout=2)
                if response.status_code == 200:
                    peers[uuid]["last_seen"] = time.time()
            except requests.RequestException:
                pass
        time.sleep(60)

def broadcast_message(message):
    message_data = {
        "sender": my_uuid,
        "sender_name": socket.gethostname(),
        "content": message,
        "timestamp": time.time()
    }
    for uuid, info in list(peers.items()):
        try:
            requests.post(f"{info['url']}/message", json=message_data, timeout=2)
        except requests.RequestException as e:
            logger.warning(f"Failed to send message to {info['url']}: {e}")

def start_server(port=5000):
    zeroconf, service_info = register_service(port)
    listener = ServiceListener()
    browser = listener.start_discovery()
    maintenance_thread = threading.Thread(target=maintenance_task, daemon=True)
    maintenance_thread.start()
    try:
        logger.info(f"Starting Flask server on port {port}")
        app.run(host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Shutting down...")
        zeroconf.unregister_service(service_info)
        zeroconf.close()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='P2P Flask server with Zeroconf')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()
    
    start_server(args.port)

