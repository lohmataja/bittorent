import bencoding
import hashlib
import requests
from bitstring import BitArray
import socket
import struct

MAX_REQUESTS = 2
MAX_CONNECTIONS = 2

class Torrent():

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
        #TODO: piece/block representation
        self.pieces = BitArray(bin='0'*self.num_pieces)

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

        self.connected = False
        self.choked = True
        self.interested = False

        self.pieces = []
        self.reply = ''

        self.requests = [] #array of tuples: piece, offset
        self.requested_pieces = [] #array of tuples representing pieces currently in work: (piece index, BitArray of blocks)
        self.MAX_REQUESTS = MAX_REQUESTS




