#!/usr/bin/env python3

from typing import Optional
from symbolic import box, Result
from tinyscript_util import (
	check_sat,
	stringify
)
import tinyscript as tn

def instrument(alpha: tn.Prog, step_bound: Optional[int]=None) -> tn.Prog:
	"""
	Instruments a program to support symbolic checking 
	for violations of the maximum execution length policy.
	
	Args:
	    alpha (tn.Prog): A tinyscript program to instrument
	    step_bound (int, optional): A bound on runtime steps
	
	Returns:
	    tn.Prog: The instrumented program. It should be possible
	    	to use the box modality and a satisfiability solver
	    	to determine whether a trace in the original program
	    	`alpha` exists that executes for longer than the bound
	    	on steps. A step occurs when the program executes an
	    	assignment, output, abort, or skip statement.
	"""
	return alpha

def symbolic_check(
	alpha: tn.Prog, 
	step_bound: int,
	max_depth: int=1,
	timeout: int=10) -> Result:
	"""
	Uses the box modality and a satisfiability solver to determine
	whether there are any traces that execute more than `step_bound`
	steps. A step occurs when the program executes an assignment, 
	output, abort, or skip statement. This function only considers 
	traces generated after unrolling loops up to `max_depth` times, 
	and will terminate the solver after `timeout` seconds.
	
	Args:
	    alpha (tn.Prog): Program to check
	    step_bound (int): Step bound to check
	    max_depth (int, optional): Loop unrolling depth
	    timeout (int, optional): Solver timeout, in seconds
	
	Returns:
	    Result: The status of the check, one of three values:
	    	- Result.Satisfies: All traces, up to the given unrolling 
	    	  depth, terminate within `step_bound` steps. 
	    	- Result.Violates: There exists a trace that violates the
	    	  step bound. This result *includes* traces that do not 
	    	  terminate within the unrolling depth, e.g., 
	    	  the program "while(true) skip" should yield this result
	    	  with an unrolling depth of 1 if the solver is able to 
	    	  provide a state that causes the interpreter to execute
	    	  at least `step_bound` steps.
	    	- Result.Unknown: The result is indeterminate. This could
	    	  mean that the solver timed out, returning z3.unknown. It
	    	  could also signify that there is a trace that fails to
	    	  terminate within the unrolling bound, but the solver did
	    	  not return a state that caused the interpreter to execute
	    	  at least `step_bound` steps.
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
			res = symbolic_check(prog, 100)
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
