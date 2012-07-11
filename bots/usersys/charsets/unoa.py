""" Python Character Mapping Codec generated from CP1252.TXT with gencodec.py.

Written by Marc-Andre Lemburg (mal@lemburg.com).

(c) Copyright CNRI, All Rights Reserved. NO WARRANTY.
(c) Copyright 2000 Guido van Rossum.

Adapted by Henk-Jan Ebbers for Bots open source EDI translator
Regular UNOA: UNOA char, CR, LF and Crtl-Z
"""

import codecs
import sys

### Codec APIs

class Codec(codecs.Codec):

    def encode(self,input,errors='strict'):

        return codecs.charmap_encode(input,errors,encoding_map)

    def decode(self,input,errors='strict'):

        return codecs.charmap_decode(input,errors,decoding_map)
        
class StreamWriter(Codec,codecs.StreamWriter):
    pass

class StreamReader(Codec,codecs.StreamReader):
    pass

### encodings module API
class IncrementalEncoder(codecs.IncrementalEncoder):
	def encode(self, input, final=False):
		return codecs.charmap_encode(input,self.errors,encoding_map)[0]

class IncrementalDecoder(codecs.IncrementalDecoder):
	def decode(self, input, final=False):
		return codecs.charmap_decode(input,self.errors,decoding_table)[0]
def getregentry():
	return codecs.CodecInfo(
		name='unoa',
		encode=Codec().encode,
		decode=Codec().decode,
		incrementalencoder=IncrementalEncoder,
		incrementaldecoder=IncrementalDecoder,
		streamreader=StreamReader,
		streamwriter=StreamWriter,
	)

### Decoding Map

#decoding_map = codecs.make_identity_dict(range(128))
#decoding_map.update({
decoding_map = {	
#	0x0000:0x0000,	  #NUL
#	0x0001:0x0000,	  #SOH
#	0x0002:0x0000,	  #STX
#	0x0003:0x0000,	  #ETX
#	0x0004:0x0000,	  #EOT
#	0x0005:0x0000,	  #ENQ
#	0x0006:0x0000,	  #ACK
#	0x0007:0x0000,	  #Bell
#	0x0008:0x0000,	  #BackSpace
#	0x0009:0x0000,	  #Tab
	0x000a:0x000a,	  #lf
#	0x000b:0x0000,	  #Vertical Tab
#	0x000c:0x0000,	  #FormFeed
	0x000d:0x000d,	  #cr
#	0x000e:0x0000,	  #SO
#	0x000f:0x0000,	  #SI
#	0x0010:0x0000,	  #DLE
#	0x0011:0x0000,	  #DC1
#	0x0012:0x0000,	  #DC2
#	0x0013:0x0000,	  #DC3
#	0x0014:0x0000,	  #DC4
#	0x0015:0x0000,	  #NAK
#	0x0016:0x0000,	  #SYN
#	0x0017:0x0000,	  #ETB
#	0x0018:0x0000,	  #CAN
#	0x0019:0x0000,	  #EM
	0x001a:0x001a,	  #SUB, cntrl-Z
#	0x001b:0x0000,	  #ESC
#	0x001c:0x0000,	  #FS
#	0x001d:0x0000,	  #GS
#	0x001e:0x0000,	  #RS
#	0x001f:0x0000,	  #US
	0x0020:0x0020,    #<space> 
	0x0021:0x0021,    #!
	0x0022:0x0022,    #"
#	0x0023:0x0023,    ##
#	0x0024:0x0024,	  #$
	0x0025:0x0025,    #%
	0x0026:0x0026,    #&
	0x0027:0x0027,	  #'
	0x0028:0x0028,    #(
	0x0029:0x0029,    #)
	0x002a:0x002a,    #*
	0x002b:0x002b,    #+
	0x002c:0x002c,    #,
	0x002d:0x002d,    #-
	0x002e:0x002e,    #.
	0x002f:0x002f,    #/
	0x0030:0x0030,    #0
	0x0031:0x0031,    #1
	0x0032:0x0032,    #2
	0x0033:0x0033,    #3
	0x0034:0x0034,    #4
	0x0035:0x0035,    #5
	0x0036:0x0036,    #6
	0x0037:0x0037,    #7
	0x0038:0x0038,    #8
	0x0039:0x0039,    #9
	0x003a:0x003a,    #:
	0x003b:0x003b,    #;
	0x003c:0x003c,    #<
	0x003d:0x003d,    #=
	0x003e:0x003e,    #>
	0x003f:0x003f,    #?
#	0x0040:0x0040,    #@
	0X0041:0X0041,    #A
	0X0042:0X0042,	  #B
	0X0043:0X0043,    #C
	0X0044:0X0044,    #D
	0X0045:0X0045,    #E
	0X0046:0X0046,    #F
	0X0047:0X0047,    #G
	0X0048:0X0048,    #H
	0X0049:0X0049,    #I
	0X004A:0X004A,    #J
	0X004B:0X004B,    #K
	0X004C:0X004C,    #L
	0X004D:0X004D,    #M
	0X004E:0X004E,	  #N
	0X004F:0X004F,    #O
	0X0050:0X0050,    #P
	0X0051:0X0051,    #Q
	0X0052:0X0052,    #R
	0X0053:0X0053,    #S
	0X0054:0X0054,    #T
	0X0055:0X0055,	  #U
	0X0056:0X0056,	  #V
	0X0057:0X0057,    #W
	0X0058:0X0058,    #X
	0X0059:0X0059,    #Y
	0X005A:0X005A,    #Z
# 	0x005b:0x005b,    #[
# 	0x005c:0x005c,    #\
# 	0x005d:0x005d,    #]
# 	0x005e:0x005e,    #^
# 	0x005f:0x005f,    #_
# 	0x0060:0x0060,    #`
# 	0x0061:0x0041,    #a
# 	0x0062:0x0042,	  #b
# 	0x0063:0x0043,    #c
# 	0x0064:0x0044,    #d
# 	0x0065:0x0045,    #e
# 	0x0066:0x0046,    #f
# 	0x0067:0x0047,    #g
# 	0x0068:0x0048,    #h
# 	0x0069:0x0049,    #i
# 	0x006a:0x004a,    #j
# 	0x006b:0x004b,    #k
# 	0x006c:0x004c,    #l
# 	0x006d:0x004d,    #m
# 	0x006e:0x004e,	  #n
# 	0x006f:0x004f,    #o
# 	0x0070:0x0050,    #p
# 	0x0071:0x0051,    #q
# 	0x0072:0x0052,    #r
# 	0x0073:0x0053,    #s
# 	0x0074:0x0054,    #t
# 	0x0075:0x0055,	  #u
# 	0x0076:0x0056,	  #v
# 	0x0077:0x0057,    #w
# 	0x0078:0x0058,    #x
# 	0x0079:0x0059,    #y
#  	0x007a:0x005a,    #z
# 	0x007b:0x007b,    #{
# 	0x007c:0x007c,    #|
# 	0x007d:0x007d,    #}
# 	0x007e:0x007e,    #~
#	0x007f:0x007f,	  #del
}

### Encoding Map

encoding_map = codecs.make_encoding_map(decoding_map)
