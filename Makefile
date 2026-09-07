ROOT_DIR      := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
EXAMPLE_DIR   ?= $(CURDIR)
CONFIG_FILE   ?= $(ROOT_DIR)/make.cfg

include $(CONFIG_FILE)

MAKE_DIR      ?= $(EXAMPLE_DIR)
LOGGING_LEVEL ?= INFO
TMP_API_LIB   ?= _$(API_LIB)
TOOLS_DIR     ?= $(ROOT_DIR)/dovetail/tools
WRITE_TO_FILE ?= True
PYTHON_EXE    ?= python
FETCH_SCHEMA  ?= False
FETCH_COMMAND ?=

ifeq ($(WRITE_TO_FILE),True)
WRITE_TO_FILE_OPT := --write_to_file
endif

.PHONY: all show_config mkdir fetch_schema classes api clean_api copy_api clean test

all: api

show_config:
	@echo Make Dir = $(MAKE_DIR)
	@echo API Name = $(API_NAME)
	@echo API Library = $(API_LIB)
	@echo Schema Dir = $(SCHEMA_DIR)
	@echo Schema File = $(SCHEMA_NAME)
	@echo Request Class = $(REQUEST_CLASS)
	@echo Response Class = $(RESPONSE_CLASS)
	@echo Fetch Schema = $(FETCH_SCHEMA)
	@echo Fetch Command = $(FETCH_COMMAND)

mkdir:
	@mkdir -p $(MAKE_DIR)/$(TMP_API_LIB)

ifeq ($(FETCH_SCHEMA),True)
fetch_schema: mkdir
	@if [ -z "$(FETCH_COMMAND)" ]; then echo "FETCH_COMMAND must be configured when FETCH_SCHEMA=True"; exit 1; fi
	@if ! command -v $(FETCH_COMMAND) >/dev/null 2>&1; then echo "Fetch command not found on PATH: $(FETCH_COMMAND)"; exit 1; fi
	$(FETCH_COMMAND) $(SCHEMA_UID) $(SCHEMA_VER) $(MAKE_DIR)/$(SCHEMA_DIR)/$(SCHEMA_NAME)
else
fetch_schema: mkdir
	@test -f $(MAKE_DIR)/$(SCHEMA_DIR)/$(SCHEMA_NAME) || (echo "Schema not found: $(MAKE_DIR)/$(SCHEMA_DIR)/$(SCHEMA_NAME)" && exit 1)
endif

classes: fetch_schema
	cd $(TOOLS_DIR); $(PYTHON_EXE) xsd_to_py_class.py --schema_file $(MAKE_DIR)/$(SCHEMA_DIR)/$(SCHEMA_NAME) --classes_file $(MAKE_DIR)/$(API_LIB)/$(API_NAME).py --logging_level $(LOGGING_LEVEL) $(WRITE_TO_FILE_OPT)

api: classes
	$(MAKE) --no-print-directory clean_api
	cd $(TOOLS_DIR); $(PYTHON_EXE) py_code_gen.py --api_name $(API_NAME) --tmp_api_lib $(MAKE_DIR)/$(TMP_API_LIB) --api_lib $(MAKE_DIR)/$(API_LIB) --request_class $(REQUEST_CLASS) $(if $(RESPONSE_CLASS),--response_class $(RESPONSE_CLASS)) --logging_level $(LOGGING_LEVEL) $(WRITE_TO_FILE_OPT)
	$(MAKE) --no-print-directory copy_api

clean_api:
	rm -f $(MAKE_DIR)/$(API_LIB)/*_request.py
	rm -f $(MAKE_DIR)/$(API_LIB)/*_response.py
	rm -f $(MAKE_DIR)/$(API_LIB)/_generated_callbacks.py

copy_api:
	@set -- $(MAKE_DIR)/$(TMP_API_LIB)/*.py; [ -e "$$1" ] || { echo "No generated API modules to copy"; exit 1; }
	cp $(MAKE_DIR)/$(TMP_API_LIB)/*.py $(MAKE_DIR)/$(API_LIB)/
	rm -rf $(MAKE_DIR)/$(TMP_API_LIB)

test:
	$(PYTHON_EXE) -m py_compile $(MAKE_DIR)/$(API_LIB)/$(API_NAME).py $(MAKE_DIR)/$(API_LIB)/*_request.py $(MAKE_DIR)/$(API_LIB)/*_response.py

clean: clean_api
	@if [ "$(SCHEMA_DIR)" != "." ]; then rm -rf $(MAKE_DIR)/$(SCHEMA_DIR); fi
	rm -rf $(MAKE_DIR)/$(TMP_API_LIB)
