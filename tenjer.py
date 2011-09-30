#!/usr/bin/env python2
# -*- coding: euc-jp -*-
###
###  tenjer.py
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

FULLWIDTH = u"　！”＃＄％＆’（）＊＋，\uff0d\u2212．／０１２３４５６７８９：；＜＝＞？" \
            u"＠ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ［＼］＾＿" \
            u"‘ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ｛｜｝"
HALFWIDTH = u" !\"#$%&'()*+,--./0123456789:;<=>?" \
            u"@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_" \
            u"`abcdefghijklmnopqrstuvwxyz{|}"
Z2HMAP = dict( (ord(zc), ord(hc)) for (zc,hc) in zip(FULLWIDTH, HALFWIDTH) )
def zen2han(s):
  return s.translate(Z2HMAP)

def decode_yomi(s):
    return u''.join( unichr(0x3000+ord(c)) for c in s )

POST = { ord(u'は'):u'わ', ord(u'へ'):u'え' }
EUPH = re.compile(ur'([オコゴソゾトドノホボポモヨロョォ])ウ')
def reg_yomi(s):
    s = s[:-1]+(s[-1].translate(POST))
    s = hira2kata(s)
    s = EUPH.sub(ur'\1ー', s)
    return s


##  CDB
##
class CDBReader(object):

    def __init__(self, cdbname):
        self.name = cdbname
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
        k = str(k)
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
        k = str(k)
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
    for c in u'"([〈《「『【〔“（［\uff62':
        KIND[c] = 6
    #for c in u')]〉》」』】〕）\］uff63':
    #    KIND[c] = 7

    POST1 = set(
        [u'を', u'が', u'は',
         u'で',u'では',u'でも',
         u'に',u'には',u'にも',
         # u'も',u'と',u'か'
         u'の',u'のを',u'のが',u'のは',u'ので',u'のに',
         u'のだ',u'のも',
         ])

    ADV1 = set(
        [u'案外', u'以来', u'依然', u'一応', u'一切', u'一瞬', u'一足', u'一晩',
         u'一律', u'各自', u'延々', u'何故', u'何卒', u'俄然', u'皆目', u'急遽',
         u'極力', u'近々', u'今更', u'最早', u'至急', u'至極', u'時々', u'順次',
         u'所詮', u'随分', u'折角', u'全然', u'早速', u'多分', u'大抵', u'大変',
         u'大方', u'沢山', u'逐一', u'丁度', u'当然', u'到底', u'突如', u'別段',
         u'本来', u'万一', u'無論', u'毛頭', u'勿論', u'以前', u'以後', u'以来',
         u'以上', u'以降', u'昨日', u'昨年', u'近日', u'近年', u'偶然', u'結局',
         u'結構', u'元来', u'後日', u'今頃', u'今後', u'今回', u'今日', u'今月',
         u'今年', u'今週', u'今度', u'今晩', u'今夜', u'再度', u'最近', u'最初',
         u'昨日', u'昨月', u'昨年', u'昨週', u'昨晩', u'昨夜', u'先程', u'先頃',
         u'先日', u'先月', u'先年', u'先週', u'先晩', u'先夜', u'前回', u'前月',
         u'全部', u'途中', u'当初', u'当日', u'当分', u'当面', u'日中', u'日頃',
         u'日夜', u'年々', u'年中', u'本日', u'毎回', u'毎月', u'毎週', u'毎朝',
         u'毎度', u'毎日', u'毎年', u'毎晩', u'明朝', u'明日', u'明晩', u'夜分',
         u'翌月', u'翌朝', u'翌日', u'翌年', u'来月', u'来週', u'来年', u'例年',
         u'連日',
         ])

    def __init__(self):
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

    def flush(self):
        if self._chunk:
            self._chunks.append(self._chunk)
            self._chunk = u''
        return
    
    def get_chunks(self):
        (r, self._chunks) = (self._chunks, [])
        return r
    
    def _parse_main(self, c, k, i):
        if k == 1:
            self._parse = self._parse_latin
        elif k == 2:
            self._parse = self._parse_tail
        elif k == 3:
            self._parse = self._parse_kata
        elif k == 4:
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
        self.flush()
        self._parse = self._parse_main
        return i

    def _parse_tail(self, c, k, i):
        if k == 2:
            # 「お願い」などの「お」は直前で切る。
            if c == u'お':
                self._parse = self._parse_tailo
                return i+1
            self._chunk += c
            # 助詞がきたら切るかもしれない。
            if c in self.POST1:
                self._parse = self._parse_tail2
            return i+1
        self._parse = self._parse_other
        return i

    def _parse_tail2(self, c, k, i):
        if k == 2:
            # 助詞が続く場合。
            if self._chunk[-1]+c in self.POST1:
                self._parse = self._parse_tail
                return i
        # 助詞が終わったので切る。
        self._parse = self._parse_other
        return i

    def _parse_tailo(self, c, k, i):
        if k == 4:
            # 「お+漢字」は「お」の前で切る。
            self.flush()
            self._chunk += u'お'
            self._parse = self._parse_kanji
            return i
        self._chunk += u'お'
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
            if self._chunk in self.ADV1:
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

    def __init__(self, dictpath=None, codec='euc-jp'):
        if dictpath is None:
            dictpath = os.path.join(os.path.dirname(__file__), 'tenjer.tcdb')
        self._tcdb = TCDBReader(dictpath)
        self.codec = codec
        return

    def yome(self, s):
        r = []
        i = 0
        (i0,i1,p,y) = (0,0,0L,None)
        while i < len(s):
            c = s[i]
            try:
                (v, p) = self._tcdb.lookup1(c.encode(self.codec, 'ignore'), p)
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
        x = u''
        a = []
        for (c,y) in r:
            if y is None:
                x += c
            else:
                if x:
                    a.append((x, reg_yomi(x)))
                    x = u''
                a.append((y, reg_yomi(y)))
        if x:
            a.append((x, reg_yomi(x)))
        return a


##  Tenjer
##
class Tenjer(object):

    NABCC = [
        (' ','',u' '),
        ('!','2346',u'ホ'),
        ('"','5',u''),
        ('#','3456',u''),
        ('$','1246',u'ケ'),
        ('%','146',u'ク'),
        ('&','12346',u'ヘ'),
        ("'",'3',u"ワ'"),
        ('(','12356',u'ミ'),
        (')','23456',u'モ'),
        ('*','16',u'カ'),
        ('+','346',u'ユ'),
        (',','6',u''),
        ('-','36',u'「」『』【】-'),
        ('.','46',u''),
        ('/','34',u'ヤ'),
        ('0','356',u'ン"'),
        ('1','2',u'ッ,'),
        ('2','23',u'ヰ;'),
        ('3','25',u'ー:'),
        ('4','256',u'。.'),
        ('5','26',u'?'),
        ('6','235',u'!'),
        ('7','2356',u'()'),
        ('8','236',u''),
        ('9','35',u'ヲ'),
        (':','156',u'サ'),
        (';','56',u'、'),
        ('<','126',u'キ'),
        ('=','123456',u'メ'),
        ('>','345',u'ヨ'),
        ('?','1456',u'ス'),
        ('@','4',u''),
        ('A','1',u'ア1A'),
        ('B','12',u'イ2B'),
        ('C','14',u'ウ3C'),
        ('D','145',u'ル4D'),
        ('E','15',u'ラ5E'),
        ('F','124',u'エ6F'),
        ('G','1245',u'レ7G'),
        ('H','125',u'リ8H'),
        ('I','24',u'オ9I'),
        ('J','245',u'ロ0J'),
        ('K','13',u'ナK'),
        ('L','123',u'ニL'),
        ('M','134',u'ヌM'),
        ('N','1345',u'ツN'),
        ('O','135',u'タO'),
        ('P','1234',u'ネP'),
        ('Q','12345',u'テQ'),
        ('R','1235',u'チR'),
        ('S','234',u'ノS'),
        ('T','2345',u'トT'),
        ('U','136',u'ハU'),
        ('V','1236',u'ヒV'),
        ('W','2456',u'ソW'),
        ('X','1346',u'フX'),
        ('Y','13456',u'ムY'),
        ('Z','1356',u'マZ'),
        ('[','246',u'コ'),
        ('\\','1256',u'シ'),
        (']','12456',u'セ'),
        ('^','45',u''),
        ('_','456',u''),
        ]

    TABLE = {
        u'ウァ':'5A', 
        u'ウィ':'5B', 
        u'ヴ':'"C',
        u'ウェ':'5F', u'イェ':'@F', 
        u'ウォ':'5I', 
        u'ガ':'"*', u'キャ':'@*', u'ギャ':'^*', u'クァ':'5*', u'グァ':'4*', 
        u'ギ':'"<', u'クィ':'5<', 
        u'グ':'"%', u'キュ':'@%', u'ギュ':'^%',
        u'ゲ':'"$', u'クェ':'5$', 
        u'ゴ':'"[', u'キョ':'@[', u'ギョ':'^[', u'クォ':'5[', 
        u'ザ':'":', u'シャ':'@:', u'ジャ':'^:',
        u'ジ':'"\\',
        u'ズ':'"?', u'シュ':'@?', u'ジュ':'^?',
        u'ゼ':'"]', u'シェ':'@]',
        u'ゾ':'"W', u'ショ':'@W', u'ジョ':'^W',
        u'ダ':'"O', u'チャ':'@O', u'ヂャ':'^O', u'ツァ':'5O', 
        u'ヂ':'"R', u'ツィ':'5R', u'ティ':'"R', u'ディ':'^R',
        u'ヅ':'"N', u'チュ':'@N', u'ヂュ':'^N', u'テュ':'.N', u'デュ':'_N', u'トゥ':'5N', u'ドゥ':'4N', 
        u'デ':'"Q', u'ツェ':'5Q', u'チェ':'@Q', u'ジェ':'^Q',
        u'ド':'"T', u'チョ':'@T', u'ヂョ':'^T', u'ツォ':'5T', 
        u'ニャ':'@K',
        u'ニュ':'@M',
        u'ニョ':'@S',
        u'バ':'"U', u'パ':',U', u'ヒャ':'@U', u'ビャ':'^U', u'ピャ':'.U', u'ファ':'5U', u'ヴァ':'4U', 
        u'ビ':'"V', u'ピ':',V', u'フィ':'5V', u'ヴィ':'4V', 
        u'ブ':'"X', u'プ':',X', u'ヒュ':'@X', u'ビュ':'^X', u'ピュ':'.X', u'フュ':'5X', u'ヴュ':'_X', 
        u'ベ':'"&', u'ペ':',&', u'フェ':'5&', u'ヴェ':'4&', 
        u'ボ':'"!', u'ポ':',!', u'ヒョ':'@!', u'ビョ':'^!', u'ピョ':'.!', u'フォ':'5!', u'ヴォ':'4!',
        u'ミャ':'@Z',
        u'ミュ':'@Y',
        u'ミョ':'@)',
        u'リャ':'@E',
        u'リュ':'@D',
        u'リョ':'@J',
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
    for c in (u'!?"([〈《「『【〔“（［\uff62'
              u')]〉》」』】〕）］\uff63'):
        KIND[c] = 3
    
    def tenji(self, chars):
        i = 0
        chars = zen2han(chars).upper()
        self._brl = []
        self._parse = self._parse_main
        self._tmp = None
        while 0 <= i and i < len(chars):
            c = chars[i]
            k = self.KIND.get(c, 0)
            i = self._parse(c, k, i)
        if self._tmp is not None:
            self._brl.append((self._tmp, self.TABLE.get(self._tmp)))
        return self._brl

    def _parse_main(self, c, k, i):
        if k == 1:
            self._brl.append((None,';'))
            self._parse = self._parse_latin
            return i
        elif k == 3:
            self._tmp = u''
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
            if (self._tmp+c) in self.TABLE:
                self._tmp += c
                return i+1
            self._brl.append((self._tmp, self.TABLE.get(self._tmp)))
            self._tmp = c
            return i+1
        self._brl.append((self._tmp, self.TABLE.get(self._tmp)))
        self._tmp = None
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
        (opts, args) = getopt.getopt(argv[1:], 'dc:w:D:')
    except getopt.GetoptError:
        return usage()
    debug = 0
    codec = 'utf-8'
    width = 32
    dictpath = None
    for (k, v) in opts:
        if k == '-d': debug += 1
        elif k == '-c': codec = v
        elif k == '-w': width = int(v)
        elif k == '-D': dictpath = v
    tenjer = Tenjer()
    yomer = Yomer(dictpath=dictpath)
    wakacher = Wakacher()
    for line in fileinput.input(args):
        line = line.decode(codec, 'ignore')
        wakacher.feed(line)
        wakacher.flush()
        r = []
        for s in wakacher.get_chunks():
            y = yomer.yome(s)
            t = u''.join( v or k for (k,v) in y)
            a = u''
            b = u''
            for (x,y) in tenjer.tenji(t):
                a += x or u''
                b += y or u''
            if debug:
                print '>', a
            r.append(b)
        for line in fold(r, width=width):
            print line
    return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
