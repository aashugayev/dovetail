ROOT_DIR := $(abspath ../..)

include make.cfg

.PHONY: all show_config mkdir fetch_schema classes api test clean

all show_config mkdir fetch_schema classes api test clean:
	$(MAKE) --no-print-directory -C $(ROOT_DIR) -f Makefile CONFIG_FILE=$(CURDIR)/make.cfg EXAMPLE_DIR=$(CURDIR) $@