import bencoding
import hashlib
import requests
from bitstring import BitArray
import socket
import struct

MAX_REQUESTS = 2
MAX_CONNECTIONS = 2
MSG_TYPES = ['choke', 'unchoke', 'interested', 'not_interested', 'have', 'bitfield', 'request', 'piece', 'cancel', 'port']
class Torrent():
    """
    Keeps track of all information associated with a particular torrent file.
    Gets and processes info from tracker, finding peers.
    Keeps track of the pieces under download, figures out what to download next, writes to file.
    """

    def __init__(self, torrent_file):
        self.torrent_data = bencoding.bdecode(open(torrent_file, 'rb').read())
        self.announce = self.torrent_data['announce']
        self.info = self.torrent_data['info']
        self.info_hash = hashlib.sha1(bencoding.bencode(self.torrent_data['info'])).digest()
        self.peer_id = 'liutorrent1234567890'
        self.uploaded = 0
        self.downloaded = 0
        self.port = 6881 #how do I choose a port? randomly within the unreserved range?
        self.filename = self.info['name'] #for now, single file only

        #handshake: <pstrlen><pstr><reserved><info_hash><peer_id>
        self.handshake = ''.join([chr(19), 'BitTorrent protocol', chr(0)*8, self.info_hash, self.peer_id])

        self.length = self.info['length'] if 'length' in self.info.keys() \
            else sum([f['length'] for f in self.info['files']])
        self.piece_len = self.info['piece length']
        self.BLOCK_LEN = 2**14
        self.num_pieces = self.length/self.piece_len + 1
        self.last_piece_len = self.length % self.piece_len
        self.last_block_len = self.piece_len % self.BLOCK_LEN
        self.blocks_per_piece = self.piece_len / self.BLOCK_LEN + 1 * (self.last_block_len != 0)
        #Pieces/blocks data: pieces BitArray represents the pieces that I have;
        #blocks is a list of BitArray, each of which keeps track of downloaded blocks
        self.pieces = BitArray(bin='0'*self.num_pieces)
        self.blocks = [BitArray(bin='0'*self.blocks_per_piece) for i in range(len())]

        self.info_from_tracker = self.update_info_from_tracker()
        self.peers = self.get_peers()

        self.num_connected = 0
        self.MAX_CONNECTIONS = MAX_CONNECTIONS
        self.requests = []

    def get_left(self):
        return self.length - self.downloaded

    def get_params(self):
        return {'info_hash':self.info_hash,
                'peer_id':self.peer_id,
                'uploaded':self.uploaded,
                'downloaded':self.downloaded,
                'port':self.port,
                'left':self.get_left(),
                'compact':1,
                'event':'started'}

    def update_info_from_tracker(self):
        tracker_response = requests.get(self.announce, params=self.get_params())
        return bencoding.bdecode(tracker_response.text)

    def get_peers(self):
        peer_bytes = [ord(byte) for byte in self.info_from_tracker['peers']]
        # assert len(peer_bytes)%6 == 0
        peers = []
        for i in range(len(peer_bytes)/6):
            ip = '.'.join([str(byte) for byte in peer_bytes[i*6:i*6+4]])
            port = peer_bytes[i*6+4]*256+peer_bytes[i*6+5]
            peers.append(Peer(ip, port))
        return peers


class Peer():

    def __init__(self, ip, port, peer_id = None):
        self.ip = ip
        self.port = port
        self.peer_id = peer_id
        self.sock = None

        self.connected = False
        self.choked = True
        self.interested = False

        self.pieces = []
        self.reply = ''

        self.requests = [] #array of tuples: piece, offset
        self.requested_pieces = [] #array of tuples representing pieces currently in work: (piece index, BitArray of blocks)
        self.MAX_REQUESTS = MAX_REQUESTS

    def encode_msg(self, msg_type, payload=''):
        if msg_type == 'keep alive':
            msg = ''
        else:
            msg = struct.pack('B', MSG_TYPES.index(msg_type))+payload
        return struct.pack('>I', len(msg))+msg

    def request(self, piece):
        #send request
        piece_idx, offset, length = piece
        self.sock.sendall(self.encode_msg('request', struct.pack('>I I I',  piece_idx, offset, length)))
        #update self.requests

    def connect(peer, torrent):
        peer.sock = socket.socket()
        #make socket non-blocking
        peer.sock.sendall(torrent.handshake)
        peer_handshake = peer.sock.recv(68)
        #TODO: verify peer_handshake
        #update peer's status:
        peer.connected = True

    def receive(self):
        """receive a reply from peer"""
        try:
            reply = self.sock.recv(1000)
            if reply:
                self.reply += reply
                msg_len = struct.unpack('>I', self.reply[:4])
                if msg_len == 0:
                    pass
                else:
                    self.msg_processor(self.reply[4:4+msg_len], self)
                    self.reply = self.reply[:4+msg_len]
        except:
            print len(peer.reply), len(reply)
    def msg_processor(self, msg_str, peer):
        msg = struct.unpack('B', msg_str[0])
        #choke
        if msg == 0:
            peer.choked = True
        #unchoke
        elif msg == 1:
            peer.choked = False
        #peer is interested
        elif msg == 2:
            self.send_msg('unchoke')
        #peer is not interested
        elif msg == 3:
            pass
        #peer has piece #x
        elif msg == 4:
            #update info about peer's pieces
            peer.pieces(msg_str[1:]) = True
        #bitfield msg
        elif msg == 5:
            peer.has_pieces = msg_str[1:] #TODO: unpack and convert to a necessary data structure
        #request for a piece
        elif msg == 6:
            pass #TODO: implement sending a piece
            #locate requested piece, send it; update uploaded, advertise it other peers
        #piece
        elif msg == 7:
            index, begin = struct.unpack('>I I', msg_str[1:9])
            self.f.seek(index*self.piece_len+begin)
            self.f.write(msg_str[9:])
            #update self.pieces, downloaded
        #cancel piece
        elif msg == 8:
            pass
        #port msg
        elif msg == 9:
            pass
        else:
            print 'unknown message:', msg, msg_str


