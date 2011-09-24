# Makefile for pubdic.tcdb

# from pubdic+
PUBDIC_DIR=pubdic-plus-wnn
# from pubdic+-sup
PUBDIC_SUP_DIR=pubdic+-sup
# from gerodic
GERODIC_DIR=gerodic

# python
PYTHON=python2
RM=rm -f

PUBDIC_FILES= \
 $(PUBDIC_DIR)/bio.u \
 $(PUBDIC_DIR)/chimei.u \
 $(PUBDIC_DIR)/computer.u \
 $(PUBDIC_DIR)/jinmei.u \
 $(PUBDIC_DIR)/kihon.u \
 $(PUBDIC_DIR)/koyuu.u \
 $(PUBDIC_DIR)/setsuji.u \
 $(PUBDIC_DIR)/tankan.u

#PUBDIC_SUP_FILES=$(PUBDIC_SUP_DIR)/supplement.u
#GERODIC_FILES=$(GERODIC_DIR)/g-jinmei.u

DICT_FILES=$(PUBDIC_FILES) $(PUBDIC_SUP_FILES) $(GERODIC_FILES) others.u

EXPAND_PUBDIC=$(PYTHON) expand_pubdic.py
BUILD_DICT=$(PYTHON) build_dict.py
OVERRIDE_ENTRY=$(PYTHON) override_entry.py

all: pubdic.tcdb

clean:
	-$(RM) pubdic.txt pubdic.tcdb

pubdic.tcdb: pubdic.txt
	$(BUILD_DICT) -o $@ pubdic.txt

pubdic.txt: $(DICT_FILES)
	$(EXPAND_PUBDIC) $(DICT_FILES) | $(OVERRIDE_ENTRY) override.txt > $@
