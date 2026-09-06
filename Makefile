ROOT_DIR      := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
EXAMPLE_DIR   ?= $(CURDIR)
CONFIG_FILE   ?= $(ROOT_DIR)/make.cfg

include $(CONFIG_FILE)

MAKE_DIR      ?= $(EXAMPLE_DIR)
LOGGING_LEVEL ?= INFO
TMP_API_LIB   ?= _$(API_LIB)
TOOLS_DIR     ?= $(ROOT_DIR)/dovetail/tools
DICTS_DIR     ?= dicts
INITS_DIR     ?= inits
STUBS_DIR     ?= stubs
WRITE_TO_FILE ?= True
PYTHON_EXE    ?= python
FETCH_SCHEMA  ?= False
FETCH_COMMAND ?=

ifeq ($(WRITE_TO_FILE), True)
	WRITE_TO_FILE_OPT=--write_to_file
else
    WRITE_TO_FILE_OPT=
endif

ifeq ($(filter show_config,$(MAKECMDGOALS)),)
DACITE := $(shell $(PYTHON_EXE) -m pip freeze | grep dacite)
ifeq ($(DACITE),)
$(error "no dacite python module detected")
endif

LXML := $(shell $(PYTHON_EXE) -m pip freeze | grep lxml)
ifeq ($(LXML),)
$(error "no lxml python module detected")
endif

REQUESTS := $(shell $(PYTHON_EXE) -m pip freeze | grep requests)
ifeq ($(REQUESTS),)
$(error "no requests python module detected")
endif
endif
 
all: api

show_config:
	@echo Showing make configuration...
	@echo Make Dir = $(MAKE_DIR)
	@echo API Name = $(API_NAME)
	@echo Schema Dir = $(SCHEMA_DIR)
	@echo Schema File = $(SCHEMA_NAME) 
	@echo Json Dics Dir = $(DICTS_DIR)
	@echo Class Inits Dir = $(INITS_DIR)
	@echo API Code Stubs Dir = $(STUBS_DIR)
	@echo Request Class Name = $(REQUEST_CLASS)
	@echo Response Class Name = $(RESPONSE_CLASS)
	@echo Write to File = $(WRITE_TO_FILE)
	@echo Write to File Opt = $(WRITE_TO_FILE_OPT)
	@echo Fetch Schema = $(FETCH_SCHEMA)
	@echo Fetch Command = $(FETCH_COMMAND)
	
mkdir:
	@echo Making $(DICTS_DIR) $(INITS_DIR) $(STUBS_DIR) $(SCHEMA_DIR) directories...
	mkdir -p $(MAKE_DIR)/$(DICTS_DIR)
	mkdir -p $(MAKE_DIR)/$(INITS_DIR)
	mkdir -p $(MAKE_DIR)/$(STUBS_DIR)
	mkdir -p $(MAKE_DIR)/$(SCHEMA_DIR)
	mkdir -p $(MAKE_DIR)/$(TMP_API_LIB)

ifeq ($(FETCH_SCHEMA), True)
fetch_schema: mkdir
	@if [ -z "$(FETCH_COMMAND)" ]; then echo "FETCH_COMMAND must be configured when FETCH_SCHEMA=True"; exit 1; fi
	@if ! command -v $(FETCH_COMMAND) >/dev/null 2>&1; then echo "Fetch command not found on PATH: $(FETCH_COMMAND)"; exit 1; fi
	@echo Fetching $(SCHEMA_NAME) schema with $(FETCH_COMMAND)...
	$(FETCH_COMMAND) $(SCHEMA_UID) $(SCHEMA_VER) $(MAKE_DIR)/$(SCHEMA_DIR)/$(SCHEMA_NAME)
else
fetch_schema: mkdir
	@test -f $(MAKE_DIR)/$(SCHEMA_DIR)/$(SCHEMA_NAME) || (echo "Schema not found: $(MAKE_DIR)/$(SCHEMA_DIR)/$(SCHEMA_NAME)" && exit 1)
endif

classes: fetch_schema
	@echo Generating api dataclasses code...
	cd $(TOOLS_DIR); $(PYTHON_EXE) xsd_to_py_class.py --schema_file $(MAKE_DIR)/$(SCHEMA_DIR)/$(SCHEMA_NAME) --classes_file $(MAKE_DIR)/$(API_LIB)/$(API_NAME).py --logging_level $(LOGGING_LEVEL) $(WRITE_TO_FILE_OPT)
	
api: classes
	@echo Generating api code...
	cd $(TOOLS_DIR); $(PYTHON_EXE) py_code_gen.py --api_name $(API_NAME) --tmp_api_lib $(MAKE_DIR)/$(TMP_API_LIB) --api_lib $(MAKE_DIR)/$(API_LIB) --dicts_dir $(MAKE_DIR)/$(DICTS_DIR) --inits_dir $(MAKE_DIR)/$(INITS_DIR) --stubs_dir $(MAKE_DIR)/$(STUBS_DIR) --request_class $(REQUEST_CLASS) $(if $(RESPONSE_CLASS),--response_class $(RESPONSE_CLASS)) --logging_level $(LOGGING_LEVEL) $(WRITE_TO_FILE_OPT)
	$(MAKE) --no-print-directory copy_api
	
test_dict:
	@echo Testing $(DICTS_DIR) json request to api request object and json responce to api response objects conversion...
	cd $(DICTS_DIR);\
	for f in *.py; do\
		echo testing $$f;\
		if [[ -n $(IGNORE_TEST) ]]; then\
			for dict in $(IGNORE_TEST); do\
				if [[ $$f =~ $$dict ]]; then\
		    		echo skipping $$f;\
		    		continue 2;\
				fi;\
			done;\
		fi;\
		PYTHONPATH=../$(API_LIB) $(PYTHON_EXE) $$f;\
	done
	
test_init:
	@echo Testing $(INITS_DIR) request and response classes instantiation...
	cd $(INITS_DIR);\
	for f in *.py; do\
		echo testing $$f;\
		if [[ -n $(IGNORE_TEST) ]]; then\
			for init in $(IGNORE_TEST); do\
				if [[ $$f =~ $$init ]]; then\
		    		echo skipping $$f;\
		    		continue 2;\
		    	fi;\
		    done;\
		fi;\
		PYTHONPATH=../$(API_LIB) $(PYTHON_EXE) $$f;\
	done
	
test_api:
	@echo Testing $(API_NAME) elements instantiation...
	cd $(TMP_API_LIB);\
	for f in *.py; do\
		echo testing $$f;\
		if [[ -n $(IGNORE_TEST) ]]; then\
			for wrap in $(IGNORE_TEST); do\
				if [[ $$f =~ $$wrap ]]; then\
		    		echo skipping $$f;\
		    		continue 2;\
		    	fi;\
		    done;\
		fi;\
		PYTHONPATH=../$(API_LIB) $(PYTHON_EXE) $$f;\
	done
	
clean_api:
	@echo Removing previously generated api code from $(API_LIB)...
	@if [ "$(API_LIB)" != "." ]; then rm -f $(MAKE_DIR)/$(API_LIB)/*.py; fi
	
copy_api:
	@echo Copying newly generated api code from $(TMP_API_LIB) to $(API_LIB)...
	@set -- $(MAKE_DIR)/$(TMP_API_LIB)/*.py; [ -e "$$1" ] || { echo "No generated API modules to copy"; exit 1; }
	cp $(MAKE_DIR)/$(TMP_API_LIB)/*.py $(MAKE_DIR)/$(API_LIB)/
	rm -rf $(MAKE_DIR)/$(TMP_API_LIB)
	
test_stub:
	@echo testing api code stubs...
	cd $(STUBS_DIR);\
	for f in *.py; do\
		echo testing $$f;\
		if [[ -n $(IGNORE_TEST) ]]; then\
			for stub in $(IGNORE_TEST); do\
				if [[ $$f =~ $$stub ]]; then\
		    		echo skipping $$f;\
		    		continue 2;\
		    	fi;\
		    done;\
		fi;\
		PYTHONPATH=../$(API_LIB) $(PYTHON_EXE) $$f;\
	done

test: test_dict test_init test_api test_stub

clean: clean_api
	rm -rf $(MAKE_DIR)/$(DICTS_DIR)
	rm -rf $(MAKE_DIR)/$(INITS_DIR)
	rm -rf $(MAKE_DIR)/$(STUBS_DIR)
	@if [ "$(SCHEMA_DIR)" != "." ]; then rm -rf $(MAKE_DIR)/$(SCHEMA_DIR); fi
	rm -rf $(MAKE_DIR)/$(TMP_API_LIB)