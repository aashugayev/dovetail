"""Developer-owned component enrichment hooks.

This file is created once and is never overwritten by py_code_gen.py.
See _generated_callbacks.py for current hook signatures.
"""


def identity(component, *, sku, name, description, brand):
	"""Provide a small example of product identity enrichment."""
	return {
		"normalized_name": name.strip(),
		"sku": str(sku),
	}
