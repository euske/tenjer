# Makefile for tenjer5

DICTFILE=tenjer.tcdb

# python
PYTHON=python2
RM=rm -f
MV=mv -f

all: $(DICTFILE)

clean:
	-cd dict && $(MAKE) clean
	-$(RM) $(DICTFILE) *.pyc *.pyo

tenjer.tcdb:
	cd dict && make pubdic.tcdb
	-$(MV) dict/pubdic.tcdb $(DICTFILE)
