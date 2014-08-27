from collections import deque
import socket
import struct
from bitstring import BitArray

MAX_REQUESTS = 2
MSG_TYPES = ['choke', 'unchoke', 'interested', 'not_interested', 'have', 'bitfield', 'request', 'piece', 'cancel', 'port']

class Peer():

    def __init__(self, torrent, ip, port, peer_id = None):
        self.torrent = torrent
        self.ip = ip
        self.port = port
        self.peer_id = peer_id
        self.sock = None
        self.handshake = ''

        self.handshake_sent = False
        self.connected = False
        self.interested_sent = False
        self.is_chocking = True
        self.am_interested = False
        self.am_choking = True
        self.is_interested = False
        self.msg_queue = deque()

        self.pieces = BitArray(bin='0'*self.torrent.num_pieces)
        self.reply = ''

        self.requests = [] #array of tuples: piece, offset
        self.requested_pieces = [] #array of tuples representing need_pieces currently in work: (piece index, BitArray of need_blocks)
        self.MAX_REQUESTS = MAX_REQUESTS
        self.MAX_MSG_LEN = 2**15

    def fileno(self):
        """
        makes Peer object behave like i/o object that can be handled by select
        will only work once self.sock has been created
        """
        return self.sock.fileno()

    def enqueue_msg(self):
        if not self.handshake_sent:
            self.msg_queue.append(self.torrent.handshake)
            self.handshake_sent = True
            print 'Enq Handshake'
        elif self.is_chocking and not self.interested_sent:
            self.msg_queue.append(self.encode_msg('interested'))
            self.interested_sent = True
            print('Enq interested')
        elif not self.is_chocking and len(self.requests) < self.MAX_REQUESTS:
            new_request = self.torrent.get_next_request(self)
            if new_request:
                index, begin, length = new_request
                self.msg_queue.append(self.encode_msg('request', struct.pack('>I I I', index, begin, length)))
                #update self.requests
                self.requests.append((index, begin))
                print 'Enq request:', new_request

    def send_msg(self):
        while self.msg_queue:
            try:
                self.sock.sendall(self.msg_queue[0])
                self.msg_queue.popleft()
            except:
                break

    def encode_msg(self, msg_type, payload=''):
        if msg_type == 'keep alive':
            msg = ''
        else:
            msg = struct.pack('B', MSG_TYPES.index(msg_type))+payload
        return struct.pack('>I', len(msg))+msg

    def update_connected(self, handshake):
        #TODO: verify peer_handshake
        print 'Received handshake', handshake
        #update peer's status:
        self.connected = True

    def update_reply(self):
        """receive a reply from peer"""
        try:
            self.reply += self.sock.recv(self.MAX_MSG_LEN)
        except socket.error:
            print socket.error

    def process_reply(self):
        while self.reply != '':
            if ord(self.reply[0]) == 19 and self.reply[1:20] == 'BitTorrent protocol':
                self.update_connected(self.reply[:68])
                self.reply = self.reply[68:]
            else:
                msg_len = struct.unpack('>I', self.reply[:4])[0]
                if msg_len == 0:
                    print 'Keep alive'
                    #TODO: keep alive: reset the timeout; update self.reply
                    self.reply = self.reply[:4]
                elif len(self.reply) >= (msg_len + 4):
                    self.process_msg(self.reply[4:4+msg_len])
                    self.reply = self.reply[4+msg_len:]
                else:
                    break

    def process_msg(self, msg_str):
        msg = struct.unpack('B', msg_str[0])[0]
        print MSG_TYPES[msg]
        #choke
        if msg == 0:
            self.is_chocking = True

        #unchoke
        elif msg == 1:
            self.is_chocking = False

        #peer is interested
        elif msg == 2:
            self.sock.sendall(self.encode_msg('unchoke'))

        #peer is not interested
        elif msg == 3:
            pass

        #peer has piece #x
        elif msg == 4:
            #update info about peer's need_pieces
            piece_idx = struct.unpack('>I', msg_str[1:])[0]
            self.pieces[piece_idx] = True

        #bitfield msg
        elif msg == 5:
            self.pieces = BitArray(bytes=msg_str[1:])
            del self.pieces[self.torrent.num_pieces:] #cut out unnecessary bits

        #request for a piece
        elif msg == 6:
            pass #TODO: implement sending a piece
            #locate requested piece, send it
            index, begin, length = struct.unpack('>I I I', msg_str[1:])
            #read the data
            data = self.torrent.read(index, begin, length)
            if data: #if read is successful
                self.enqueue_msg(self.encode_msg('piece', struct.pack('>I I', index, begin) + data))
            #update uploaded
            self.torrent.uploaded += length

        #piece
        elif msg == 7:
            index, begin = struct.unpack('>I I', msg_str[1:9])
            #write the file
            self.torrent.write(index, begin, msg_str[9:])
            #update the peer's queue
            self.requests.remove((index, begin))

        #cancel piece
        elif msg == 8:
            pass

        #port msg
        elif msg == 9:
            pass

        else:
            print 'unknown message:', msg, msg_str
