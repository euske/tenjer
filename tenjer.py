#!/usr/bin/env python2
# -*- coding: euc-jp -*-
###
###  tenjer.py
###
###  Copyright (c) 2011  Yusuke Shinyama <yusuke at cs dot nyu dot edu>
###
###  Permission is hereby granted, free of charge, to any person
###  obtaining a copy of this software and associated documentation
###  files (the "Software"), to deal in the Software without
###  restriction, including without limitation the rights to use,
###  copy, modify, merge, publish, distribute, sublicense, and/or
###  sell copies of the Software, and to permit persons to whom the
###  Software is furnished to do so, subject to the following
###  conditions:
###
###  The above copyright notice and this permission notice shall be
###  included in all copies or substantial portions of the Software.
###  
###  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
###  KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
###  WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
###  PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
###  COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
###  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
###  OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
###  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
### 

import sys, re, os.path
from struct import pack, unpack
from array import array


##  utilities
##
def cdbhash(s, n=5381L):
    return reduce(lambda h,c: ((h*33) ^ ord(c)) & 0xffffffffL, s, n)

if pack('=i',1) == pack('>i',1):
    # big endian
    def decode(x):
        a = array('I', x)
        a.byteswap()
        return a
    def encode(a):
        a.byteswap()
        return a.tostring()
else:
    # little endian
    def decode(x):
        a = array('I', x)
        return a
    def encode(a):
        return a.tostring()

HIRA2KATA = dict( (c, c+96) for c in xrange(0x3041,0x3094) )
def hira2kata(s):
    return s.translate(HIRA2KATA)

FULLWIDTH = u"�����ɡ������ǡʡˡ��ܡ�\uff0d\u2212�������������������������������䡩" \
            u"�����£ãģţƣǣȣɣʣˣ̣ͣΣϣУѣңӣԣգ֣ףأ٣ڡΡ��ϡ���" \
            u"�ƣ���������������������������������Сá�"
HALFWIDTH = u" !\"#$%&'()*+,--./0123456789:;<=>?" \
            u"@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_" \
            u"`abcdefghijklmnopqrstuvwxyz{|}"
Z2HMAP = dict( (ord(zc), ord(hc)) for (zc,hc) in zip(FULLWIDTH, HALFWIDTH) )
def zen2han(s):
  return s.translate(Z2HMAP)

def decode_yomi(s):
    return u''.join( unichr(0x3000+ord(c)) for c in s )

POST = { ord(u'��'):u'��', ord(u'��'):u'��' }
EUPH = re.compile(ur'([�����������ȥɥΥۥܥݥ���祩])��')
def reg_yomi(s):
    s = s[:-1]+(s[-1].translate(POST))
    s = hira2kata(s)
    s = EUPH.sub(ur'\1��', s)
    return s


##  CDB
##
class CDBReader(object):

    def __init__(self, cdbname, codec):
        self.name = cdbname
        self.codec = codec
        self._fp = file(cdbname, 'rb')
        hash0 = decode(self._fp.read(2048))
        self._hash0 = [ (hash0[i], hash0[i+1]) for i in xrange(0, 512, 2) ]
        self._hash1 = [ None ] * 256
        (self._eod,_) = self._hash0[0]
        return

    def __repr__(self):
        return '<CDBReader: %r>' % self.name

    def __getstate__(self):
        raise TypeError

    def __setstate__(self, dict):
        raise TypeError

    def __getitem__(self, k):
        k = k.encode(self.codec, 'ignore')
        h = cdbhash(k)
        h1 = h & 0xff
        (pos_bucket, ncells) = self._hash0[h1]
        if ncells == 0: raise KeyError(k)
        hs = self._hash1[h1]
        if hs == None:
            self._fp.seek(pos_bucket)
            hs = decode(self._fp.read(ncells * 8))
            self._hash1[h1] = hs
        i = ((h >> 8) % ncells) * 2
        n = ncells*2
        for _ in xrange(ncells):
            p1 = hs[i+1]
            if p1 == 0: raise KeyError(k)
            if hs[i] == h:
                self._fp.seek(p1)
                self._lastpos = self._fp.tell()
                (klen, vlen) = unpack('<II', self._fp.read(8))
                k1 = self._fp.read(klen)
                if k1 == k:
                    v1 = self._fp.read(vlen)
                    return v1
            i = (i+2) % n
        raise KeyError(k)

    def close(self):
        self._fp.close()
        return

    def get(self, k, failed=None):
        try:
            return self.__getitem__(k)
        except KeyError:
            return failed

    def has_key(self, k):
        try:
            self.__getitem__(k)
            return True
        except KeyError:
            return False

    def __contains__(self, k):
        return self.has_key(k)


##  TCDB
##
class TCDBReader(CDBReader):

    def lookup(self, seq, parent=0L):
        r = []
        for k in seq:
            (v, parent) = self.lookup1(k, parent)
            r.append(v)
        return r

    def lookup1(self, k, parent=0L):
        k = k.encode(self.codec, 'ignore')
        h = cdbhash(k, parent+5381L)
        self._fp.seek((h % 256) << 3)
        (pos_bucket, ncells) = unpack('<II', self._fp.read(8))
        if ncells == 0: raise KeyError(k)
        start = (h >> 8) % ncells
        for i in xrange(ncells):
            self._fp.seek(pos_bucket + ((start+i) % ncells << 3))
            (h1, p1) = unpack('<II', self._fp.read(8))
            if p1 == 0: raise KeyError(k)
            if h1 == h:
                self._fp.seek(p1)
                (klen, vlen) = unpack('<II', self._fp.read(8))
                k1 = self._fp.read(klen)
                if k1 == k:
                    v1 = self._fp.read(vlen)
                    return (v1,p1)
        raise KeyError(k)


##  Wakacher
##
class Wakacher(object):

    KIND = {}
    for (i1,i2,k) in (
        (0x0040, 0x005a, 1), # latin
        (0x0060, 0x007a, 1),
        (0xff21, 0xff3a, 1),
        (0xff41, 0xff5a, 1),
        (0x3041, 0x3093, 2), # hira
        (0x30a1, 0x30f4, 3), # kata
        (0x30fc, 0x30fc, 3), # kata
        (0xff66, 0xff9f, 3),
        (0x3005, 0x3007, 4), # kanji
        (0x4e00, 0x9fff, 4), # kanji
        (0x0030, 0x0039, 5), # digit
        (0x002e, 0x002e, 5),
        (0xff10, 0xff19, 5),
        ):
        for i in xrange(i1,i2+1):
            KIND[unichr(i)] = k
    for c in u'"([�ҡԡ֡ءڡ̡ȡʡ�\uff62':
        KIND[c] = 6
    #for c in u')]�ӡաס١ۡ͡�\��uff63':
    #    KIND[c] = 7

    PREFIX1 = set(
        [u'��'
         ])

    POST1 = {
        u'��': u'',
        u'��': u'�ä������',
        u'��': u'',
        u'��': u'�����������Ϥ��',
        u'��': u'�Ϥ�',
        # u'��',u'��',u'��'
        u'��': u'�򤬤ϤǤˤ���',
        }

    ADV1 = set(
        [u'�Ƴ�', u'����', u'����', u'���', u'����', u'���', u'��­', u'����',
         u'��Χ', u'�Ƽ�', u'�䡹', u'����', u'��´', u'����', u'����', u'���',
         u'����', u'�᡹', u'����', u'����', u'���', u'���', u'����', u'�缡',
         u'����', u'��ʬ', u'�޳�', u'����', u'��®', u'¿ʬ', u'����', u'����',
         u'����', u'����', u'���', u'����', u'����', u'����', u'��ǡ', u'����',
         u'����', u'����', u'̵��', u'��Ƭ', u'����', u'����', u'�ʸ�', u'����',
         u'�ʾ�', u'�ʹ�', u'����', u'��ǯ', u'����', u'��ǯ', u'����', u'���',
         u'�빽', u'����', u'����', u'����', u'����', u'����', u'����', u'����',
         u'��ǯ', u'����', u'����', u'����', u'����', u'����', u'�Ƕ�', u'�ǽ�',
         u'����', u'���', u'��ǯ', u'��', u'����', u'����', u'����', u'�躢',
         u'����', u'���', u'��ǯ', u'�轵', u'����', u'����', u'����', u'����',
         u'����', u'����', u'����', u'����', u'��ʬ', u'����', u'����', u'����',
         u'����', u'ǯ��', u'ǯ��', u'����', u'���', u'���', u'�轵', u'��ī',
         u'����', u'����', u'��ǯ', u'����', u'��ī', u'����', u'����', u'��ʬ',
         u'���', u'��ī', u'����', u'��ǯ', u'���', u'�轵', u'��ǯ', u'��ǯ',
         u'Ϣ��',
         ])

    MAXCONTKANJI = 2

    def __init__(self, tcdb):
        self._tcdb = tcdb
        self.reset()
        return
    
    def reset(self):
        self._chunks = []
        self._chunk = u''
        self._parse = self._parse_main
        return

    def feed(self, chars):
        i = 0
        while 0 <= i and i < len(chars):
            c = chars[i]
            k = self.KIND.get(c, 0)
            i = self._parse(c, k, i)
        return

    def get_chunks(self, chars):
        self.reset()
        self.feed(chars)
        self._flush()
        (r, self._chunks) = (self._chunks, [])
        return r
    
    def _flush(self):
        if self._chunk:
            self._chunks.append(self._chunk)
            self._chunk = u''
        return
    
    def _parse_main(self, c, k, i):
        if k == 1:
            self._parse = self._parse_latin
        elif k == 2:
            self._parse = self._parse_tail
        elif k == 3:
            self._parse = self._parse_kata
        elif k == 4:
            self._dstate = 0
            self._parse = self._parse_kanji
        elif k == 5:
            self._parse = self._parse_digit
        elif k == 6:
            self._parse = self._parse_paren
        else:
            self._parse = self._parse_other
        return i

    def _parse_other(self, c, k, i):
        if k == 0:
            self._chunk += c
            return i+1
        self._flush()
        self._parse = self._parse_main
        return i

    def _parse_tail(self, c, k, i):
        if k == 2:
            # �֤��ꤤ�פʤɤΡ֤��פ�ľ�����ڤ롣
            if c in self.PREFIX1:
                self._prechunk = c
                self._parse = self._parse_tailpre
                return i+1
            self._chunk += c
            # ���줬�������ڤ뤫�⤷��ʤ���
            if c in self.POST1:
                self._parse = self._parse_tail2
            return i+1
        self._parse = self._parse_other
        return i

    def _parse_tail2(self, c, k, i):
        if k == 2:
            # ���줬³����硣
            c0 = self._chunk[-1]
            if (c0 in self.POST1 and c in self.POST1[c0]):
                self._parse = self._parse_tail
                return i
        # ���줬����ä��Τ��ڤ롣
        self._parse = self._parse_other
        return i

    def _parse_tailpre(self, c, k, i):
        if k == 4:
            # �֤�+�����פϡ֤��פ������ڤ롣
            self._flush()
            self._chunk += self._prechunk
            self._dstate = 0
            self._parse = self._parse_kanji
            return i
        self._chunk += self._prechunk
        self._parse = self._parse_tail
        return i

    def _parse_latin(self, c, k, i):
        if k == 1 or k == 5:
            self._chunk += c
            return i+1
        self._parse = self._parse_tail
        return i

    def _parse_kata(self, c, k, i):
        if k == 3:
            self._chunk += c
            return i+1
        self._parse = self._parse_tail
        return i
        
    def _parse_kanji(self, c, k, i):
        if k == 4:
            try:
                (_, self._dstate) = self._tcdb.lookup1(c, self._dstate)
            except KeyError:
                self._dstate = 0
                # MAXCONTKANJI ʸ���ʾ�δ���ñ��Τ��Ȥ��ڤ롣
                if self.MAXCONTKANJI <= len(self._chunk):
                    self._parse = self._parse_other
                    return i
            self._chunk += c
            return i+1
        self._parse = self._parse_tail
        return i
    
    def _parse_digit(self, c, k, i):
        if k == 5:
            self._chunk += c
            return i+1
        self._parse = self._parse_main
        return i

    def _parse_paren(self, c, k, i):
        if k == 6:
            self._chunk += c
            return i+1
        self._parse = self._parse_main
        return i


##  Yomer
##
class Yomer(object):

    DIGIT = {
        u'ǯ': u'�ͥ�',
        u'��': u'����',
        u'��': u'�˥�',
        u'��': u'��',
        u'��': u'�˥�',
        u'��': u'����',
        }

    def __init__(self, tcdb):
        self._tcdb = tcdb
        self.reset()
        return

    def reset(self):
        self._chunks = []
        self._part = u''
        self._yomi = None
        self._dstate = 0
        self._parse = self._parse_main
        return

    def feed(self, chars):
        i = 0
        while 0 <= i and i < len(chars):
            c = chars[i]
            i = self._parse(c, i)
        return

    def get_yomi(self, chars):
        self.reset()
        self.feed(chars)
        self._flush()
        x = u''
        a = []
        for (c,y) in self._chunks:
            if y is None:
                x += c
            else:
                if x:
                    a.append((x, reg_yomi(x)))
                    x = u''
                a.append((y, reg_yomi(y)))
        if x:
            a.append((x, reg_yomi(x)))
        return [a]

    def _flush(self):
        if self._yomi is not None:
            (n,y) = self._yomi
            self._chunks.append((self._part[:n], decode_yomi(y)))
            self._part = self._part[n:]
        if self._part:
            self._chunks.append((self._part, None))
        self._part = u''
        self._yomi = None
        return
    
    def _parse_main(self, c, i):
        self._part += c
        try:
            (v, self._dstate) = self._tcdb.lookup1(c, self._dstate)
            if v:
                self._yomi = (len(self._part), v)
        except KeyError:
            self._dstate = 0
            self._flush()
        return i+1
    
    def _get_yomi(self, s):
        r = []
        i = 0
        (i0,i1,p,y) = (0,0,0L,None)
        while i < len(s):
            c = s[i]
            try:
                (v, p) = self._tcdb.lookup1(c, p)
                i += 1
                if v:
                    (y,i1) = (v,i)
                continue
            except KeyError:
                pass
            if i0 < i1:
                r.append((s[i0:i1], decode_yomi(y)))
                i = i0 = i1
            else:
                r.append((c, None))
                i += 1
                i0 = i1 = i
            (p,y) = (0L,None)
        if y is not None:
            r.append((s[i0:i1], decode_yomi(y)))
        if i1 < len(s):
            r.append((s[i1:], None))
        return [a]


##  Tenjer
##
class Tenjer(object):

    NABCC = [
        (' ','',u' '),
        ('!','2346',u'��'),
        ('"','5',u''),
        ('#','3456',u''),
        ('$','1246',u'��'),
        ('%','146',u'��'),
        ('&','12346',u'��'),
        ("'",'3',u"��'"),
        ('(','12356',u'��'),
        (')','23456',u'��'),
        ('*','16',u'��'),
        ('+','346',u'��'),
        (',','6',u''),
        ('-','36',u'�֡סء١ڡ�-'),
        ('.','46',u''),
        ('/','34',u'��'),
        ('0','356',u'��"'),
        ('1','2',u'��,'),
        ('2','23',u'��;'),
        ('3','25',u'��:'),
        ('4','256',u'��.'),
        ('5','26',u'?'),
        ('6','235',u'!'),
        ('7','2356',u'()'),
        ('8','236',u''),
        ('9','35',u'��'),
        (':','156',u'��'),
        (';','56',u'��'),
        ('<','126',u'��'),
        ('=','123456',u'��'),
        ('>','345',u'��'),
        ('?','1456',u'��'),
        ('@','4',u''),
        ('A','1',u'��1A'),
        ('B','12',u'��2B'),
        ('C','14',u'��3C'),
        ('D','145',u'��4D'),
        ('E','15',u'��5E'),
        ('F','124',u'��6F'),
        ('G','1245',u'��7G'),
        ('H','125',u'��8H'),
        ('I','24',u'��9I'),
        ('J','245',u'��0J'),
        ('K','13',u'��K'),
        ('L','123',u'��L'),
        ('M','134',u'��M'),
        ('N','1345',u'��N'),
        ('O','135',u'��O'),
        ('P','1234',u'��P'),
        ('Q','12345',u'��Q'),
        ('R','1235',u'��R'),
        ('S','234',u'��S'),
        ('T','2345',u'��T'),
        ('U','136',u'��U'),
        ('V','1236',u'��V'),
        ('W','2456',u'��W'),
        ('X','1346',u'��X'),
        ('Y','13456',u'��Y'),
        ('Z','1356',u'��Z'),
        ('[','246',u'��'),
        ('\\','1256',u'��'),
        (']','12456',u'��'),
        ('^','45',u''),
        ('_','456',u''),
        ]

    TABLE = {
        u'����':'5A', 
        u'����':'5B', 
        u'��':'"C',
        u'����':'5F', u'����':'@F', 
        u'����':'5I', 
        u'��':'"*', u'����':'@*', u'����':'^*', u'����':'5*', u'����':'4*', 
        u'��':'"<', u'����':'5<', 
        u'��':'"%', u'����':'@%', u'����':'^%',
        u'��':'"$', u'����':'5$', 
        u'��':'"[', u'����':'@[', u'����':'^[', u'����':'5[', 
        u'��':'":', u'����':'@:', u'����':'^:',
        u'��':'"\\',
        u'��':'"?', u'����':'@?', u'����':'^?',
        u'��':'"]', u'����':'@]',
        u'��':'"W', u'����':'@W', u'����':'^W',
        u'��':'"O', u'����':'@O', u'�¥�':'^O', u'�ĥ�':'5O', 
        u'��':'"R', u'�ĥ�':'5R', u'�ƥ�':'"R', u'�ǥ�':'^R',
        u'��':'"N', u'����':'@N', u'�¥�':'^N', u'�ƥ�':'.N', u'�ǥ�':'_N', u'�ȥ�':'5N', u'�ɥ�':'4N', 
        u'��':'"Q', u'�ĥ�':'5Q', u'����':'@Q', u'����':'^Q',
        u'��':'"T', u'����':'@T', u'�¥�':'^T', u'�ĥ�':'5T', 
        u'�˥�':'@K',
        u'�˥�':'@M',
        u'�˥�':'@S',
        u'��':'"U', u'��':',U', u'�ҥ�':'@U', u'�ӥ�':'^U', u'�ԥ�':'.U', u'�ե�':'5U', u'����':'4U', 
        u'��':'"V', u'��':',V', u'�ե�':'5V', u'����':'4V', 
        u'��':'"X', u'��':',X', u'�ҥ�':'@X', u'�ӥ�':'^X', u'�ԥ�':'.X', u'�ե�':'5X', u'����':'_X', 
        u'��':'"&', u'��':',&', u'�ե�':'5&', u'����':'4&', 
        u'��':'"!', u'��':',!', u'�ҥ�':'@!', u'�ӥ�':'^!', u'�ԥ�':'.!', u'�ե�':'5!', u'����':'4!',
        u'�ߥ�':'@Z',
        u'�ߥ�':'@Y',
        u'�ߥ�':'@)',
        u'���':'@E',
        u'���':'@D',
        u'���':'@J',
        }
    for (b,_,s) in NABCC:
        for c in s:
            TABLE[c] = b
    
    KIND = {}
    for (i1,i2,k) in (
        (0x0040, 0x005a, 1), # latin
        (0x0060, 0x007a, 1),
        (0x002c, 0x002e, 1), 
        (0x003a, 0x003b, 1), 
        (0x30a1, 0x30f4, 3), # kata
        (0x30fc, 0x30fc, 3), # kata
        (0x0030, 0x0039, 5), # digit
        ):
        for i in xrange(i1,i2+1):
            KIND[unichr(i)] = k
    for c in (u'!?"([�ҡԡ֡ءڡ̡ȡʡ�\uff62'
              u')]�ӡաס١ۡ͡ˡ�\uff63'):
        KIND[c] = 3
    
    def get_brl(self, chars):
        i = 0
        chars = zen2han(chars).upper()
        self._brl = []
        self._parse = self._parse_main
        self._part = None
        while 0 <= i and i < len(chars):
            c = chars[i]
            k = self.KIND.get(c, 0)
            i = self._parse(c, k, i)
        if self._part is not None:
            self._brl.append((self._part, self.TABLE.get(self._part)))
        return self._brl

    def _parse_main(self, c, k, i):
        if k == 1:
            self._brl.append((None,';'))
            self._parse = self._parse_latin
            return i
        elif k == 3:
            self._part = u''
            self._parse = self._parse_kata
            return i
        elif k == 5:
            self._brl.append((None,'#'))
            self._parse = self._parse_digit
            return i
        else:
            return i+1

    def _parse_latin(self, c, k, i):
        if k == 1:
            self._brl.append((c, self.TABLE.get(c)))
            return i+1
        elif k == 3 or k == 5:
            self._brl.append((None, ' '))
        self._parse = self._parse_main
        return i

    def _parse_kata(self, c, k, i):
        if k == 3:
            if (self._part+c) in self.TABLE:
                self._part += c
                return i+1
            self._brl.append((self._part, self.TABLE.get(self._part)))
            self._part = c
            return i+1
        self._brl.append((self._part, self.TABLE.get(self._part)))
        self._part = None
        self._parse = self._parse_main
        return i

    def _parse_digit(self, c, k, i):
        if c == '.':
            self._brl.append((c, '1'))
            return i+1
        elif k == 5:
            self._brl.append((c, self.TABLE.get(c)))
            return i+1
        elif k == 3:
            self._brl.append((None, '_'))
        self._parse = self._parse_main
        return i

# fold
def fold(words, width=40, sep=u' '):
    r = []
    i = 0
    for w in words:
        if r and width < i+len(w):
            yield sep.join(r)
            r = []
            i = 0
        r.append(w)
        i += len(w)
    if r:
        yield sep.join(r)
    return

# main
def main(argv):
    import getopt, fileinput
    def usage():
        print 'usage: %s [-d] [-c codec] [-w width] [-D dictpath] [file ...]' % argv[0]
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'dw:c:C:D:')
    except getopt.GetoptError:
        return usage()
    debug = 0
    width = 32
    codec = 'utf-8'
    dictcodec = 'euc-jp'
    dictpath = os.path.join(os.path.dirname(__file__), 'tenjer.tcdb')
    for (k, v) in opts:
        if k == '-d': debug += 1
        elif k == '-w': width = int(v)
        elif k == '-c': codec = v
        elif k == '-C': dictcodec = v
        elif k == '-D': dictpath = v
    tcdb = TCDBReader(dictpath, dictcodec)
    tenjer = Tenjer()
    yomer = Yomer(tcdb)
    wakacher = Wakacher(tcdb)
    for line in fileinput.input(args):
        line = line.decode(codec, 'ignore')
        r = []
        for s in wakacher.get_chunks(line):
            for y in yomer.get_yomi(s):
                t = u''.join( v or k for (k,v) in y)
                a = u''
                b = u''
                for (x,y) in tenjer.get_brl(t):
                    a += x or u''
                    b += y or u''
                if debug:
                    print '>', a
                r.append(b)
        for line in fold(r, width=width):
            print line
    return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
