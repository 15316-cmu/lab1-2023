#!/usr/bin/env python3

from symbolic import box, Result
from tinyscript_util import (
	check_sat,
	stringify
)
import tinyscript as tn

def instrument(alpha: tn.Prog) -> tn.Prog:
	"""
	Instruments a program to support symbolic checking 
	for violations of the define-before-use policy.
	
	Args:
	    alpha (tn.Prog): A tinyscript program to instrument
	
	Returns:
	    tn.Prog: The instrumented program. It should be possible
	    	to use the box modality and a satisfiability solver
	    	to determine whether a trace in the original program
	    	`alpha` exists that uses an undefined variable.
	"""
	return alpha

def symbolic_check(
	alpha: tn.Prog, 
	max_depth: int=1,
	timeout: int=10
) -> Result:
	"""
	Uses the box modality and a satisfiability solver to determine
	whether there are any traces that attempt to use an undefined
	variable. This function only considers traces generated after
	unrolling loops up to `max_depth` times, and will terminate
	the solver after `timeout` seconds.
	
	Args:
	    alpha (tn.Prog): Program to check
	    max_depth (int, optional): Loop unrolling depth
	    timeout (int, optional): In seconds; if `None`, then the
	    	solver cannot timeout
	
	Returns:
	    Result: The status of the check, one of three values:
	    	- Result.Satisfies: All traces, up to the given unrolling 
	    	  depth, only attempt to use variables that were previously
	    	  defined. This result *does not* signify anything about
	    	  traces that exceed the unrolling depth.
	    	- Result.Violates: There exists a trace within the unrolling
	    	  depth that attempts to use an undefined variable.
	    	- Result.Unknown: The result is indeterminate (e.g. the
	    	  solver timed out, returning z3.unknown).

	"""
	return Result.Unknown

if __name__ == "__main__":
	from parser import parse, fmla_parse
	import sys
	from pathlib import Path

	TEST_DIR = Path('.') / 'tests'

	if not TEST_DIR.is_dir():
		raise ValueError(f"Expected {TEST_DIR} to be a directory")

	passed = 0
	violate = 0
	unknown = 0

	for test_file in list(TEST_DIR.iterdir()):
		if not str(test_file).endswith('tinyscript'):
			continue
		with test_file.open() as f:
			prog = parse(f.read())
			res = symbolic_check(prog)
			print((
				f"{test_file} result:" 
				f"{res}"))
			match res:
				case Result.Satisfies:
					passed += 1
				case Result.Violates:
					violate += 1
				case Result.Unknown:
					unknown += 1

	print(f"\n{passed=}, {violate=}, {unknown=}")
