#!/usr/bin/env python
# -*- coding: euc-jp -*-
import sys
stdout = sys.stdout
stderr = sys.stderr


HIRA2KATA = dict( (unichr(c),unichr(c+96)) for c in xrange(0x3041,0x3094) )
def tokata(s): return ''.join( HIRA2KATA.get(c,c) for c in s )


##  expand_pubdic
##
def expand_pubdic(args, encoding='euc-jp', verbose=0):
  import re, fileinput
  
  VALID_WORD = re.compile(ur'^[々〆ヵヶ\u4e00-\u9fff][々〆\u3041-\u309f\u4e00-\u9fff]*$')
  RMSP = re.compile(r'\s+')
  POS_EXPAND = {
    u'カ行五段': u'かきくけこい',
    u'ガ行五段': u'がぎぐげごい',
    u'サ行五段': u'さしすせそ',
    u'タ行五段': u'たとつてとっ',
    u'ナ行五段': u'なにぬねのん',
    u'マ行五段': u'まみむめもん',
    u'ラ行五段': u'らりるれろっ',
    u'ワ行五段': u'わいうえおっ',
    u'バ行五段': u'ばびぶべぼん',
    u'形容詞': u'かきくけい',
    }

  dic = {}
  pos_freq = {}
  
  fp = fileinput.input(args)
  for line in fp:
    if fp.isfirstline():
      print '# filename=%r' % fp.filename()
    try:
      line = unicode(line.strip(), encoding)
    except UnicodeError:
      print >>stderr, 'UnicodeError: filename=%r, lineno=%d' % \
            (fp.filename(), fp.filelineno())
      continue
    if not line: continue
    
    f = RMSP.sub(' ', line).split(' ')
    if len(f) == 4:
      (yomi,exp,poss,_) = f
    else:
      print >>stderr, 'FormatError: filename=%r, lineno=%d: %r' % \
            (fp.filename(), fp.filelineno(), line)
      continue

    if not VALID_WORD.match(exp) and poss != '-': continue
    for pos1 in poss.split('&'):
      r = POS_EXPAND.get(pos1, [''])
      for c in r:
        w = exp+c
        if w not in dic:
          dic[w] = []
        y = tokata(yomi+c)
        d = dic[w]
        if y not in d:
          d.append(y)
      if pos1 not in pos_freq:
        pos_freq[pos1] = 0
      pos_freq[pos1] += 1
      
  for w in sorted(dic.iterkeys()):
    print ('%s %s' % (w, ' '.join(dic[w]))).encode(encoding)

  if verbose:
    for pos1 in sorted(pos_freq.iterkeys()):
      print >>stderr, '%s: %d' % (pos1, pos_freq[pos1])
  return


# main
def main(argv):
  import getopt
  def usage():
    print 'usage: %s [file ...]' % argv[0]
    return 100
  try:
    (opts, args) = getopt.getopt(argv[1:], '')
  except getopt.GetoptError:
    return usage()
  return expand_pubdic(args)

if __name__ == '__main__': sys.exit(main(sys.argv))
