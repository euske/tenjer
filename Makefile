# Makefile for tenjer

DICTFILE=tenjer.tcdb

# python
PYTHON=python2
RM=rm -f
MV=mv -f

all: $(DICTFILE)

clean:
	-cd dict && $(MAKE) clean
	-$(RM) $(DICTFILE) *.pyc *.pyo

test: all
	$(PYTHON) tenjer.py -d -ceuc-jp README

$(DICTFILE):
	cd dict && make pubdic.tcdb
	-$(MV) dict/pubdic.tcdb $(DICTFILE)

pack: tenjer.tcdb tenjer.py README
	cd .. && tar zcf /tmp/tenjer.tar.gz tenjer/tenjer.py tenjer/tenjer.tcdb tenjer/README
