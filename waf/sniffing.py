
import threading
from scapy.all import sniff, Raw
import scapy.all as scapy
from scapy.layers.http import HTTPRequest, HTTP
from scapy.layers.inet import IP, TCP
from scapy.sessions import IPSession, TCPSession
import urllib.parse
from request import Request, DBController
from classifier import ThreatClassifier
from argparse import ArgumentParser
from .constants import header_fields

arg_parser = ArgumentParser()
arg_parser.add_argument('--port', type=int, default=5000, help='Defines which port to sniff')
args = arg_parser.parse_args()

scapy.packet.bind_layers(TCP, HTTP, dport=args.port)
scapy.packet.bind_layers(TCP, HTTP, sport=args.port)

db = DBController()
thread_clf = ThreatClassifier()


def get_header(packet):
	headers = {}
	for field in header_fields:
		f = getattr(packet[HTTPRequest], field)
		if f != None and f != 'None':
			headers[field] = f.decode()

	return headers

def sniff_method(packet):
	# only sniff http requests
	if packet.haslayer(HTTPRequest):
		req = Request()
		if packet.haslayer(IP):
			req.origin = packet[IP].src
		else:
			req.origin = 'localhost'

		req.host = urllib.parse.unquote(packet[HTTPRequest].Host.decode())
		req.request = urllib.parse.unquote(packet[HTTPRequest].Path.decode())
		req.method = packet[HTTPRequest].Method.decode()
		req.headers = get_header(packet)
		req.threat_type = 'None'

		if packet.haslayer(Raw):
			req.body = packet[Raw].load.decode()

		thread_clf.classify_request(req)
		db.save(req)

def start_sniffing():
	pkgs = sniff(prn=sniff_method, iface='lo', filter='port ' + str(args.port) + ' and inbound',session=TCPSession)
	db.close()
