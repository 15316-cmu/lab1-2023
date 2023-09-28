#!/bin/bash

if test -f "handin.zip"; then
	rm handin.zip
fi
zip -r handin.zip . -x .git/**\* -x .git\* -x src/__pycache__/**\* -x src/__pycache__\* -x tests\* -x test/**\*