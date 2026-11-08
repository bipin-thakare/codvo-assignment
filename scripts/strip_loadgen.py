#!/usr/bin/env python3
"""Drop the built-in loadgenerator Deployment/Service from a multi-doc manifest."""
import re, sys
docs = open(sys.argv[1]).read().split("\n---\n")
keep = [d for d in docs if not re.search(r"^\s*name:\s*loadgenerator\s*$", d, re.M)]
print("\n---\n".join(keep))
