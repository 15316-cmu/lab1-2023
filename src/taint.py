#!/usr/bin/env python3

from symbolic import box, Result
from tinyscript_util import (
	check_sat,
	fmla_enc,
	state_from_z3_model,
	stringify,
	vars_formula,
	vars_prog,
	vars_term,
)
from functools import reduce
import interpreter as interp
import tinyscript as tn
import z3

def instrument(alpha: tn.Prog, source_prefix: str='sec_') -> tn.Prog:
	"""
	Instruments a program to support symbolic checking 
	for violations of a taint policy that considers any variable 
	prefixed with `secret_prefix` to be a source, and the argument 
	to any `output` statement to be a sink.
	
	Args:
	    alpha (tn.Prog): A tinyscript program to instrument
	    source_prefix (str, optional): The string prefix for
	    	source variables
	
	Returns:
	    tn.Prog: The instrumented program. It should be possible
	    	to use the box modality and a satisfiability solver
	    	to determine whether a trace in the original program
	    	`alpha` exists that violates the taint policy.
	"""
	return alpha

def symbolic_check(
	alpha: tn.Prog, 
	source_prefix: str='sec_', 
	max_depth: int=1,
	timeout: int=10) -> Result:
	"""
	Uses the box modality and a satisfiability solver to determine
	whether there are any traces that violate a taint policy that 
	considers any variable prefixed with `secret_prefix` to be a 
	source, and the argument to any `output` statement to be a sink.
	This function only considers traces generated after unrolling 
	loops up to `max_depth` times, and will terminate the solver 
	after `timeout` seconds.
	
	Args:
	    alpha (tn.Prog): Program to check
	    source_prefix (str, optional): String prefix for source
	    	variables
	    max_depth (int, optional): Loop unrolling depth
	    timeout (int, optional): Solver timeout, in seconds
	
	Returns:
	    Result: The status of the check, one of three values:
	    	- Result.Satisfies: All traces up to the unrolling depth
	    	  satisfy the taint policy. This result *does not* signify 
	    	  anything about traces that exceed the unrolling depth.
	    	- Result.Violates: There exists a trace within the unrolling
	    	  depth that violates the taint policy.
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