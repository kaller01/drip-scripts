#!/bin/python

# HTT Consulting, LLC
# Robert Moskowitz
# 2023-07-25

# developed with Fedora 35 using
# dnf install python3-pycryptodomex
# https://pycryptodome.readthedocs.io/en/v3.15.0/src/introduction.html
# dnf install python3-IPy

__version__ = '2023.07.25'

import sys, getopt
from subprocess import call, DEVNULL

import hashlib
import math
from binascii import *
import base64
from IPy import IP
from Cryptodome.PublicKey import ECC
from Cryptodome.Hash import cSHAKE128

DATA_SET_SIZE = 1000000

def det_orchid(keyname, raa, hda, hi):
	# ORCHID PREFIX = 2001:30/28 = b0010 0000 0000 0001:0000 0000 0011/28
	# HID = RAA (always 14 bits) + HDA (always 14 bits) = 10 + 20 = b00 0000 0000 1010 + b00 0000 0000 0001 0100

	b_prefix = '0010000000000001000000000011' # RFC 9374 Section 8.2.1
	h_prefix = '2001003'
	suiteid = 5

	b_ogaid = '00000101' # RFC 9374 Section 8.2.2
	h_ogaid = suiteid
	ContextID = unhexlify("00B5A69C795DF5D5F0087F56843F2C40")


	#format the HID from raa and HDA
#	print("raa:", raa)
#	print("RAA:", f'{raa:014b}')
#	print("HDA:", f'{hda:014b}')
	b_hid = f'{raa:014b}' + f'{hda:014b}'
#	print("HID:", b_hid)

	# perform hash with cSHAKE using input data
	h_orchid_left = unhexlify(hex(int(b_prefix + b_hid + b_ogaid, 2))[2:])
#	print(h_orchid_left.hex())
	shake =  cSHAKE128.new(custom = ContextID)
	shake.update((h_orchid_left + hi))
	h_hash = shake.read(8).hex()
#	print(h_hash)

	# format orchid in binary
	h_orchid = hex(int(b_prefix + b_hid + b_ogaid, 2))[2:] + h_hash

	# add in ':' for IPv6
	print("DET:", h_orchid)
#	print(hi.hex())
	hiprr = base64.b64encode(hi).decode('ascii')
#	print(hiprr)
	print("HIP RR: IN  HIP ( 5 ", h_orchid, "\n        ", hiprr, ")")
	#, hiprr[52:].zfill(52), ")")
	orchid = ':'.join(h_orchid[i:i+4] for i in range(0, len(h_orchid), 4))
	print("DET:", orchid)
	fqdn = h_hash + '.' + f'{suiteid:02x}' + "." + f'{raa:04x}' + "." + f'{hda:04x}' + "." + h_prefix + ".det.uas."
	print("FQDN:", fqdn) 
	ip = IP(orchid)
	revip = ip.reverseName()
	print("Reverse:", revip)
	keynamedat = keyname + ".dat"
	f = open(keynamedat,'wt')
	f.write("DETofC=0x" + h_orchid +"\n")
	f.write("HIofC=0x" + hi.hex() +"\n")
	f.write('pkeyname="' + keyname + '"\n')
	f.close()

	return orchid

def main(argv):
	print("DET Gen Version: ", __version__)
	# set some defaults
	keyname = 'keyfile'
	passwd = ''
	suiteid = 5
	raa = 16376
	hda = 20

	createkeyname = False

	# handle cmdline args
	try:
		opts, args = getopt.getopt(argv,"hn:p:c:",["keyname=","passwd=","suiteid=","raa=","hda=", "keynameexists="])
	except getopt.GetoptError:
		print('Error')
		sys.ext(2)

	# parse the args
	for opt, arg in opts:
		if opt == '-h':
			print('det-gen.py [-n,--keyname] <keyname> [-p,--passwd] <password> [--suiteid <HIT Suite ID:4> --raa <RAA:10> --hda <HDA:20> --keynameexists <y/n>]')
			sys.exit()
		elif opt in ("-n", "--keyname"):
			keyname = arg
		elif opt in ("-p", "--passwd"):
			passwd = arg
		elif opt == '--suiteid':
			suiteid = int(arg)
		elif opt == '--raa':
			raa = int(arg)
		elif opt == '--hda':
			hda = int(arg)
		elif opt == '--keynameexists':
			if arg == 'n' or arg == 'N':
				createkeyname = True
			else:
				createkeyname = False

	# show value we will be using
	print("Using the following value for DET generation:")
	print("KEY file: ", keyname)
	print("KEY PASSWORD: ", passwd)
	print("HHIT Suite ID: ", suiteid)
	print("RAA: ", raa)
	print("HDA: ", hda)
	prkeyname = keyname + "prv.pem"
	pbkeyname = keyname + "pub.pem"
	pbkeynameder = keyname + "pub.der"
	if createkeyname:
		key = ECC.generate(curve='ed25519')
		f = open(prkeyname,'wt')
		f.write(key.export_key(format='PEM'))
		f.close()
		f = open(prkeyname,'rt')
		prkey = ECC.import_key(f.read())
#		print("EdDSA: ", prkey)
		f = open(pbkeyname,'wt')
		pbkey = key.public_key()
		pbpem = key.public_key().export_key(format="PEM")
#		print("EdDSA: ", pbkey)
#		print("EdDSA: ", pbpem)
		f.write(pbpem)
		f.close()
		pbder = key.public_key().export_key(format="DER")
		print("PK DER: ", pbder.hex())
		print("TLSA RR: IN  TLSA 3 1 0 (", pbder.hex()[:44].zfill(44), "\n        ", pbder.hex()[44:].zfill(44), ")")
		f = open(pbkeynameder,'wb')
		f.write(pbder)
		f.close()
		pbraw = key.public_key().export_key(format="raw")
	else:
		f = open(prkeyname,'rt')
		prkey = ECC.import_key(f.read())
		f.close()
		pbraw = prkey.public_key().export_key(format="raw")
		pbder = prkey.public_key().export_key(format="DER")
		print("PK DER: ", pbder.hex())
		print("TLSA RR: IN  TLSA 3 1 0 (", pbder.hex()[:44].zfill(44), "\n        ", pbder.hex()[44:].zfill(44), ")")

	print("Raw HI: ", pbraw.hex())
	HOST_ID = unhexlify('00010000') + pbraw # RFC 9374 Section 3.4.1.1
	det = det_orchid(keyname, raa, hda, HOST_ID)




if __name__ == "__main__":
	main(sys.argv[1:])
