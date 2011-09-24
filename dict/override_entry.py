#!/usr/bin/env python2
import sys
import fileinput

def main(argv):
    args = argv[1:]
    codec = 'euc-jp'
    d = {}
    fp = file(args.pop(0))
    for line in fp:
        line = line.strip()
        if not line or line.startswith('#'): continue
        f = line.decode(codec).split(' ')
        (k,v) = f
        d[k] = v
    fp.close()
    for line in fileinput.input(args):
        line = line.strip()
        if not line or line.startswith('#'): continue
        f = line.decode(codec).split(' ')
        w = f[0]
        if w in d:
            y = d[w]
        else:
            y = f[1]
        print (w+' '+y).encode(codec)
    return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
