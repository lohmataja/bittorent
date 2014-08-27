import bencoding
import hashlib
import requests
from collections import deque
from bitstring import BitArray
from peer import Peer

MAX_OUTGOING_CONNECTIONS = 1
MAX_INCOMING_CONNECTIONS = 1
BLOCK_LEN = 2**14

class Torrent():
    """
    Keeps track of all information associated with a particular torrent file.
    Gets and processes info from tracker, finding peers.
    Keeps track of the need_pieces under download, figures out what to download next, writes to file.
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
        self.filename = './'+self.info['name'] #for now, single file only
        with open(self.filename, 'wb') as f:
            pass
        #handshake: <pstrlen><pstr><reserved><info_hash><peer_id>
        self.handshake = ''.join([chr(19), 'BitTorrent protocol', chr(0)*8, self.info_hash, self.peer_id])

        self.length = self.info['length'] if 'length' in self.info.keys() \
            else sum([f['length'] for f in self.info['files']])
        self.piece_len = self.info['piece length']
        self.block_len = BLOCK_LEN

        self.last_piece_len = self.length % self.piece_len
        self.num_pieces = self.length/self.piece_len + 1 * (self.last_piece_len != 0)
        self.last_piece = self.num_pieces - 1
        self.last_block_len = self.piece_len % self.block_len
        self.blocks_per_piece = self.piece_len / self.block_len + 1 * (self.last_block_len != 0)
        #Pieces/need_blocks data: need_pieces BitArray represents the pieces that I need and have not requested;
        #need_blocks is a list of BitArray, each of which keeps track of blocks not yet requested
        self.need_pieces = BitArray(bin='1'*self.num_pieces)
        self.need_blocks = [BitArray(bin='1'*self.blocks_per_piece) for i in range(self.num_pieces)]
        self.have_pieces = BitArray(bin='0'*self.num_pieces)
        self.have_blocks = [BitArray(bin='0'*self.blocks_per_piece) for i in range(self.num_pieces)]

        self.info_from_tracker = self.update_info_from_tracker()
        self.peers = self.get_peers()
        self.active_peers = []

        self.num_connected = 0
        self.max_outgoing_connections = MAX_OUTGOING_CONNECTIONS
        self.max_incoming_connections = MAX_INCOMING_CONNECTIONS
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
        peers = deque()
        for i in range(len(peer_bytes)/6):
            ip = '.'.join([str(byte) for byte in peer_bytes[i*6:i*6+4]])
            port = peer_bytes[i*6+4]*256+peer_bytes[i*6+5]
            peers.append(Peer(self, ip, port))
        return peers

    def write(self, index, begin, data):
        #write data to file
        with open(self.filename, 'r+b') as f:
            f.seek(index*self.piece_len+begin)
            f.write(data)
            print 'piece', index, begin, 'written'
        #update downloaded, have_blocks and have_pieces
        self.downloaded += len(data)
        self.have_blocks[index][begin/self.block_len] = True
        if self.have_blocks[index].count(0) == 0:
            self.have_pieces[index] = True

    def read(self, index, begin, length):
        #currently not handling length discrepancies
        with open(self.filename, 'r+b') as f:
            f.seek(index*self.piece_len+begin)
            return f.read(length)

    def get_next_request(self, peer):
        """
        takes Torrent and Peer objects and finds the next block to download
        """
        diff = peer.pieces & self.need_pieces
        #find next piece that the peer has and I don't have
        try:
            piece_idx = next(i for i in range(len(diff)) if diff[i] == True)
            print 'Next piece:', piece_idx, self.need_blocks[piece_idx].bin
            #find next block in that piece that I don't have
            block_idx = next(i for i in range(self.blocks_per_piece) if self.need_blocks[piece_idx][i] == True)
            # print block_idx
        except StopIteration:
            return None
        offset = block_idx * self.block_len
        length = self.last_piece_len if piece_idx == self.last_piece else min(self.block_len, self.piece_len - offset)
        #update need_blocks and need_pieces
        self.need_blocks[piece_idx][block_idx] = False
        if self.need_blocks[piece_idx].count(1) == 0:
            self.need_pieces[piece_idx] = False
        return piece_idx, offset, length
