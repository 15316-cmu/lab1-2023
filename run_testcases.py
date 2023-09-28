#!/usr/bin/env python3

def score(r: str, t: str) -> float:
	if r == t:
		return 1.
	else:
		if r == str(Result.Unknown):
			if t == str(Result.Violates):
				return 0.75
			else:
				return 0.25
		else:
			return 0.

if __name__ == "__main__":
	import sys
	import json
	from pathlib import Path

	sys.path.append('src')

	from parser import parse, fmla_parse
	from symbolic import Result
	import runtime
	import defuse
	import taint

	TEST_DIR = Path('.') / 'tests'

	if not TEST_DIR.is_dir():
		raise ValueError(f"Expected {TEST_DIR} to be a directory")

	with open('tests/groundtruth.json', 'r') as f:
		truth = json.load(f)

	results = {}

	for test_file in list(TEST_DIR.iterdir()):
		if not str(test_file).endswith('tinyscript'):
			continue
		with test_file.open() as f:
			prog = parse(f.read())
			runtime_res = runtime.symbolic_check(prog, 100)
			defuse_res = defuse.symbolic_check(prog)
			taint_res = taint.symbolic_check(prog)

			true_i = truth[str(test_file)]
			runtime_score = score(str(runtime_res), true_i['runtime'])
			defuse_score = score(str(defuse_res), true_i['defuse'])
			taint_score = score(str(taint_res), true_i['taint'])

			results = (results | {
				str(test_file): {'runtime': runtime_score,
								 'defuse': defuse_score,
								 'taint': taint_score}}
				)
			print(f"{test_file}:", json.dumps(results[str(test_file)]))

	runtime_total = sum([results[k]['runtime'] for k in results.keys()])
	defuse_total = sum([results[k]['defuse'] for k in results.keys()])
	taint_total = sum([results[k]['taint'] for k in results.keys()])

	print((
		f"\ntotals:" 
		f"\n\truntime={runtime_total}/100" 
		f"\n\tdefuse={defuse_total}/100" 
		f"\n\ttaint={taint_total}/100"))
	print(f"\toverall={runtime_total+defuse_total+taint_total}/300")