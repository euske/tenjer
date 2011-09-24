#!/usr/bin/env python2
# -*- coding: euc-jp -*-
import sys
stdout = sys.stdout
stderr = sys.stderr


# encode the yomigana.
def encode_yomi(s):
  def f(n):
    if (0x30a1 <= n and n <= 0x30f4) or n == 0x30fc:
      return chr(n-0x3000)
    raise ValueError(n)
  try:
    return ''.join( f(ord(c)) for c in s )
  except ValueError:
    raise ValueError(repr(s))

CAN_TRANS = {
  u'ヂ': u'ジ',
  u'ヅ': u'ズ',
  #u'ヲ': u'オ',
  #u'ヴ': u'ブ',
  }


##  build_dict
##
def build_dict(output, files, codec):
  import fileinput
  from pycdb import tcdbmake

  # find the length of the common prefix of s1 and s2.
  def common_prefix(s1, s2):
    s = zip(s1, s2)
    for (i,(c1,c2)) in enumerate(s):
      if c1 != c2: break
    else:
      i = len(s)
    return i

  maker = tcdbmake(output, output+'.tmp')
  w0 = ''
  stderr.write('Writing %r...' % output)
  stderr.flush()
  for line in fileinput.input(files):
    line = line.strip()
    if not line or line.startswith('#'): continue
    f = line.decode(codec).split(' ')
    assert 2 <= len(f)
    (w,y) = (f[0], f[1])
    n = common_prefix(w0, w)
    i = n+1
    #print w, xs
    for c in w[n:-1]:
      maker.put(i, c.encode(codec), '')
      i += 1
    y = y.translate(CAN_TRANS)
    maker.put(i, w[-1].encode(codec), encode_yomi(y))
    w0 = w
  maker.finish()
  stderr.write('finished.\n')
  return


# main
def main(argv):
  import getopt
  def usage():
    print 'usage: %s [-o output] [-c codec] [file ...]' % argv[0]
    return 100
  try:
    (opts, args) = getopt.getopt(argv[1:], 'o:c:')
  except getopt.GetoptError:
    return usage()
  output = None
  codec = 'euc-jp'
  for (k, v) in opts:
    if k == '-o': output = v
    elif k == '-c': codec = v
  if output is None:
    return usage()
  return build_dict(output, args, codec=codec)

if __name__ == '__main__': sys.exit(main(sys.argv))
