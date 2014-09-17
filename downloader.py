import select
import socket
import pickle
from torrent import Torrent
from peer import Peer

HOST = '0.0.0.0'
PORT = 6886

def main_loop(torrent):
    """
    :param torrent: Torrent object
    downloads the torrent
    """
    # initialize
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((HOST, PORT))
    listener.listen(5)

    inputs = [listener]
    outputs = [listener]


    # event loop
    while torrent.get_left():
        while len(inputs) < torrent.MAX_CONNECTIONS and torrent.peers:
            peer = torrent.peers.pop() #get a new peer
            peer.sock = socket.socket() #create a socket for him
            peer.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #set socket reuse
            peer.sock.setblocking(False) #make the socket non-blocking
            try:
                peer.sock.connect((peer.ip, peer.port)) #connect
            except socket.error:
                print('connection failed', peer.ip)
            #set peer's status
            peer.state = 'sending_to_wait'
            inputs.append(peer)
            outputs.append(peer)

        #get what is ready
        to_read, to_write, errors = select.select(inputs, outputs, inputs)
        for item in to_read:
            #TODO: accept only if doesn't exceed max_incoming_connections
            if item == listener:
                new_peer_sock, new_peer_address = listener.accept()
                new_peer_sock.setblocking(False)
                #create new peer
                new_peer = Peer(torrent, *new_peer_address)
                #give it the newly created sock
                new_peer.sock = new_peer_sock
                #set state
                new_peer.state = 'waiting_to_send'
            else: #It's a peer!
                item.receive_data()
                item.process_reply()
        for item in to_write: #to_write only contains peers
            item.enqueue_msg()
            item.send_msg()
        for item in errors:
            #remove peer from select's queue
            inputs.remove(item)
            outputs.remove(item)
            #put the peer in the back of the torrent's queue of peers
            torrent.peers.appendleft(item)
            #reset peer's values and queues
            item.teardown()

def serialize(object, filename):
    with open(filename, 'wb') as f:
        pickle.dump(object, f)
def deserialize(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)

tor_f = 'C:/flagfromserver.torrent'
t = Torrent(tor_f)
main_loop(t)
