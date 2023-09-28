# Lab 1: Analyzing Safety

In this lab, you will apply what you have learned about dynamic logic, safety policies, and code instrumentation to implement a set of automated analysis tools for several safety properties. Your goal is to provide automated safety tools for a setting in which untrusted users can submit scripts in a simple language called `tinyscript` to a processing server, which executes their code on shared state and returns results via an `output` command.

### Contents

* [Analyzing Safety](#analyzing-safety)
	* [Learning goals](#learning-goals)
	* [Getting started](#getting-started)
* [Implementing safety checkers](#implementing-safety-checkers)
	* [The language `tinyscript`](#the-language-tinyscript)
	* [Analysis workflow](#analysis-workflow)
		* [Example](#example)
	* [Implementation requirements](#implementation-requirements)
		* [Box modality](#box-modality)
		* [Bounded execution](#bounded-execution)
		* [Variables are always defined before use](#variables-are-always-defined-before-use)
		* [Taint analysis](#taint-analysis)
* [Utility code](#utility-code)
* [What to hand in](#what-to-hand-in)
* [Evaluation](#evaluation)

### Learning goals

* Develop fundamental symbolic analysis primitives for new language constructs given an implementation of their interpreter.
* Use these primitives to analyze more complex safety properties by developing task-specific code instrumentation procedures.
* Understand how to use bounded verification to accomplish different types of analysis goals.
* Gain experience with Z3, a general-purpose solver that is widely used in safety tools and other applications.

### Getting started

Clone this repository onto your local machine or your Andrew home directory.

You will need to use Python 3.10 to complete this lab. We encourage you to set up a fresh virtual environment before continuing.

* Create a new conda environment.
```
$ conda create -n py310 python=3.10
```
This may not work if you are using a version of `conda` prior to 4.11. If you do not have `conda`, or need to upgrade, you can [download the latest installer](https://docs.conda.io/en/latest/miniconda.html). If you already have a recent version on your system, but not Python 3.10, then you can run:
```
$ conda install -c conda-forge python=3.10
```
After installing Python 3.10 (or if you already have it), create a new environment as described above. You can use the environment by running:
```
$ conda activate py310
```
In the new environment, install the `z3-solver` package.
```
(py310)$ pip install z3-solver
```

#### Windows users

You should be able to follow the instructions above in either of Windows' native shells, `cmd.exe` and `Powershell`. However, the course staff has not recently tested this path; we will try to help you address issues that arise, but our ability to do so may be limited depending on your system configuration.

There are two alternatives that you should consider using.
* If you are running Windows 10 version 2004 and higher (Build 19041 and higher) or Windows 11, then you can run all of these commands from the Windows Subsystem for Linux (WSL2). [See the documentation for setting this up.](https://learn.microsoft.com/en-us/windows/wsl/install) This lab was tested in Windows using the Ubuntu distribution available in the Windows App store, so if you are having trouble getting set up natively, then this is the most likely route to success.
* Use the Andrew linux cluster, where Python 3.10 is already installed as `python3`. You can install the `z3-solver` package with pip.

## Implementing safety checkers

### The language `tinyscript`

The grammar below describes the syntax of programs in `tinyscript`. Note that all of the features from the first imperative language studied in class are present, in addition to the new commands `output`, `skip`, and `abort`.

```
<program> ::= skip
            | x := <aexp>
            | output <aexp>
            | <program> ; <program>
            | if <bexp> then <program> else <program> endif
            | while <bexp> do <prog> done
            | abort
<aexp>    ::= c                                                 // integer constant
            | x                                                 // variable
            | (<aexp>)                                          // parenthesis
            | <aexp> + <aexp>
            | <aexp> - <aexp>
            | <aexp> * <aexp>
<bexp>    ::= true
            | false
            | !<bexp>
            | (<bexp>)
            | <bexp> && bexp
            | <bexp> || bexp
            | <aexp> == <aexp>
            | <aexp> < <aexp>
```

We do not provide a formal semantics of the language, but we do provide a reference interpreter in `src/interpreter.py`. A goal of this lab is to use your understanding of the semantics, based largely on this reference, to infer the relevant aspects of semantics as needed to complete the lab.

The essential functionality is implemented in `exc`:
```python
def exc(
    state: tn.State,
    alpha: tn.Prog,
    max_steps: int=None,
    quiet: bool=False
) -> tuple[tn.State, Status, int]:
```
The two required arguments of this function, `state` and `alpha`, represent the variable-to-value mapping that the program `alpha` will execute in. Optionally, `max_steps` can be specified to ensure that the interpreter will only execute `alpha` for a bounded amount of time. The flag `quiet` can be set to `True` to prevent the interpreter from printing error messages to standard output.

The semantics implemented in `exc` are similar to what we have seen in lecture, apart from a few key differences.

* There is an additional component of program states that captures the effects of `output` statements. Examining `exc` in the case of `output(e)`, observe that the only change in state is to the special "variable" `#stdout`: this variable is set to the value obtained by evaluating `e`.
* We do not assume that states map all variables to values. This means that terms appearing in a program may refer to a variable that has not yet been defined, as in the following program. When this occurs, the program does not enter an error state, but instead simply terminates.
* The `skip` statement has no effect, and simply carries over the state in which it is executed.
* The `abort` command does not change the state, but halts the interpreter entirely. For example, the program `while(true) abort` has traces that consist of a single state, which is whatever initial state the program is executed in.

To resolve any uncertainties that you may have about the semantics of `tinyscript`, you should devise test cases to run with the provided interpreter.

### Analysis workflow

The properties that you will implement checkers for cannot be expressed as postconditions in dynamic logic box formulas. Rather, they are safety properties that place constraints on intermediate states of the traces generated by a program. Regardless, they can be analyzed using the box modality after the target program has been instrumented appropriately. The approach that you should take to implementing each property `P` is as follows.

1. Write a routine that accepts a program `alpha`, and produces a modified version `alpha'` that includes instructions which keep track of whether `P` is satisfied. Formally, it should be the case that there is a postcondition `P'` such that `[alpha'] P'` is valid if and only if the original program, `alpha`, satisfies property `P`.
2. Given a program `alpha` to check, apply the instrumentation in (1), derive the corresponding postcondition `P'`, and apply the axioms of dynamic logic to derive an arithmetic formula `Q` equivalent to `[alpha'] P'`. Note that `alpha` may contain loops, so the formula derived at this step may only account for finite traces of `alpha` that correspond to finite unrolling of its loops. The way that this is handled will be particular to the property being checked.
3. Use Z3, a tool for determining the satisfiability of arithmetic constraints, to check the validity of `Q`. Recall that a formula is valid if and only if its negation is unsatisfiable. Additionally, any assignment which makes `not(Q)` true corresponds to an initial state that will cause `alpha` to violate `P`---assuming the implementation of the box modality, and the instrumentation, is correct.

Each analyzer will return a status result taking one of the following values:

* `Result.Satisfies`: The instrumented program `alpha'` satisfies its postcondition `P'` when its loops are unrolled up to the specified depth. This does not necessarily mean that `alpha` will *always* satisfy `P`, as it may be the case that there are traces that are only possible at larger unrolling depths that violate the property. Whether these traces are accounted for in a `Result.Satisfies` status depends on the property; see the subsection "implementation requirements" below.
* `Result.Violates`: There exists a trace of `alpha` that violates `P`. For some properties, this only reflects traces that are generated by unrolling loops up to the specified bounds, while for others it means that *either* a trace up to the unrolling bound violates `P`, or there may be a trace past the bound that violates `P`. See the "implementation requirements" section for details on each property.
* `Result.Unknown`: The traces of `alpha` could not be checked to determine satisfaction. This could mean that Z3 exceeded its runtime bound, and returned `z3.unknown`. See "implementation requirements" for details.

#### Example

Suppose that we wish to enforce the invariant property `x < 0` on the following program `alpha`.
```
x := i;
while x < (i-i)-1 do
    x := x + 1
done
```
We might instrument `alpha` as `alpha'` below, using the special variable `#violated` to keep track of whether the invariant is maintained.
```
if !(x < 0) then
    #violated := 1
else
    #violated := 0
endif;
if !(i > 0) then
    skip
else
    #violated := 1
endif
x := i;
while x < (i-i)-1 do
    if !(x + 1 < 0) then
        #violated := 1
    else
        skip
    endif;
    x := x + 1
done
```
Observe that the desired property holds of `alpha` and `alpha'`: `[alpha'] (#violated = 0)` is valid if and only if the invariant `x < 0` is true on the traces of `alpha`.

If we assume the precondition `x > 0`, then the invariant will hold on `alpha`, i.e. the formula `x > 0 -> [alpha'] (#violated = 0)` is valid. However, because `i` is unbounded, it does not matter how much the loop in unrolled in evaluating `[alpha'] (#violated = 0)`: if we want the analysis to be conservative, and return `Result.Satisfies` only when it is certain that unrolling loops to greater depths will not lead to a violation, then the analysis will always return `Result.Violates` or `Result.Unknown`.
* It would return `Result.Violates` if it could generate an assignment that satisfies `not([alpha'] (#violated = 0))` that, when used as an initial state to run `alpha` in, causes the interpreter to enter a state that violates the invariant `x < 0`.
* It would return `Result.Unknown` if it concluded that the formula obtained by evaluating `[alpha'] (#violated = 0)` up to the given unrolling depth is not valid, but did not find a satisfying assignment that causes the interpreter to violate the invariant.

### Implementation requirements

You will use the workflow described above to implement automated safety checkers for three safety properties, described below. However, you must first complete the implementation of the box modality, which will be used by all three analyses.

* For each of the functions described below, **your solution should maintain the original signature**. 
* You should implement as many helper functions as you need, and you are also free to change the default values of numeric optional arguments (i.e., `max_depth`, `timeout`).
* Your instrumentation may add new variables that are not referenced in the target program under analysis. You should prefix these variables with the character `#`, and should assume that none of the test cases will refer to variables starting with `#`.
* The handin API requires timeouts on calls to Z3's satisfiability checks. To ensure that these are honored, make use of the provided utility function `check_sat` in `tinyscript_util.py`.

#### Box modality

Complete the implementation of the box modality, a template of which is provided in `src/symbolic.py`.

```python
def box(
    alpha: tn.Prog,
    postcondition: z3.BoolRef,
    max_depth: int=10,
    depth_exceed_strict: bool=True
) -> z3.BoolRef:
    """
    Apply the axioms of dynamic logic to convert a box formula to
    and equivalent box-free formula over integer arithmetic. If
    the program has loops, then the loop axiom is applied up to
    `max_depth` times. After reaching this bound, `box` returns
    `z3.BoolVal(False)` if `depth_exceed_strict` is `True`, and 
    `z3.BoolVal(True)` otherwise.

    Args:
        alpha (tn.Prog): Program inside the box formula
        postcondition (z3.BoolRef): Formula outside the box
        max_depth (int, optional): Recursion limit for loop axiom; 
            defaults to `10`.
        depth_exceed_strict (bool, optional): Flags strict
            verification conditions for traces that exceed the
            loop recursion bound; defaults to `True`.
    
    Returns:
        z3.BoolRef: Result of applying axioms
    
    Raises:
        TypeError: `alpha` isn't a valid tinyscript program
    """
```

You may find it helpful to begin filling in the cases covered in lecture; you should determine whether they need modifications to account for the semantic differences between the `tinyscript` language and the one covered in lecture.

The cases not covered in lecture include `skip`, `output`, and `abort`. You should consult the reference implementation of the interpreter to understand the semantics of these instructions, and derive the corresponding axioms for the box modality.

#### Bounded execution

To ensure that user-provided scripts do not consume too many resources, scripts should terminate within 100 execution steps. A "step" is the execution of an assignment, `output`, `skip`, or `abort` command. You will find the template for this checker in `runtime.py`.

First implement the instrumentation routine `instrument.`
```python
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
```
Test your implementation of `instrument` to ensure that your instrumentation does not change the semantics of the original program, modulo any variables that you add. Additionally, manually examining instrumented versions of several programs for which you know the ground truth is advised.

Implement a procedure `symbolic_check` that uses `instrument` and `box` to check that programs terminate within 100 steps.
```python
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
```
Note that this check should, by default, assume that any path that exceeds the unrolling depth violates the policy. However, it may be possible to refine this by evaluating `alpha` on initial states that your analysis has determined might violate the policy: generate an initial state from a satisfying assignment derived from the result of `box`, and run the interpreter on this state. If it does not execute at least `step_bound` steps, then return `Result.Unknown.` If you choose to implement this functionality, then the utility function `state_from_z3_model` in `tinyscript_util.py` may prove useful.

#### Variables are always defined before use

Before executing a script, it is helpful to check to see if doing so will yield an interpreter error stemming from the use of undefined variables. You will provide an implementation of this analysis in `src/defuse.py`.

First implement the instrumentation routine `instrument.`
```python
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
```
As with the previous property, you are encouraged to test your instrumentation procedure on scripts for which you know the ground truth (i.e., whether they use undefined variables).

When your instrumentation procedure is complete, proceed to the symbolic check.
```python
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
```
Note that unlike the bounded execution checker, the `symbolic_check` that you write for this analysis should *not* return `Result.Violates` if the only traces determined to potentially violate the policy exceed the maximum unrolling depth. For example, the analysis should return `Result.Satisfies` on the following program, when run with `max_depth=99`.
```
i := 0;
while i < 100 do
    i := i + 1
done;
if i >= 100 then
    output j
else
    skip
endif
```

#### Taint analysis

In some cases, scripts may be run in situations where "secret" variables are pre-loaded into the initial state. This checker should ensure that these variables are not leaked to `#stdout`, modulo via implicit flows. Your implementation of this checker should be placed in `src/taint.py`.

The instrumentation function accepts a program and a prefix string for source variables.
```python
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
```
The instrumentation that this generates should initialize taint state for any variable beginning with `source_prefix` to "tainted", and the taint state for all other variables to "untainted". It should ensure when taintedness propagates to an argument of `output`, it is evident in the final state.

As with the other checkers, proceed to implement the symbolic check after testing your instrumenter.
```python
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
```
Similar to the define-before-use policy, this checker should only return `Result.Violates` when the taint policy is violated within the unrolling depth. The following program should yield `Result.Satisfies` for `max_depth <= 99`, and `Result.Violates` for larger `max_depth`.
```
i := 0;
while i < 100 do
    i := i + 1
done;
if i >= 100 then
    output sec_1
else
    skip
endif
```

## Utility code

Before developing your implementation, you should have a look in `tinyscript_util.py`. This file contains several utility functions that are likely to be helpful with the tasks described above.
* `check_sat` interfaces with `z3` to determine the satisfiability of a given set of constraints. It is type-compatible with `box` (`symbolic.py`), and it takes an optional `timeout` argument that is compatible with the `symbolic_check` functions in `runtime.py`, `defuse.py`, and `taint.py`.
* `term_enc` and `fmla_enc` are implementations of the Z3 encoders covered in the live coding lectures.
* `term_stringify`, `formula_stringify`, and `stringify` are pretty-printers for `tinyscript.Term`, `tinyscript.Formula`, and `tinyscript.Program` objects, respectively.
* `vars_term`, `vars_formula`, and `vars_prog` return the variables appearing in a `tinyscript.Term`, `tinyscript.Formula`, and `tinyscript.Program` object, respectively.
* `state_from_z3_model` accepts a model produced by Z3 (i.e., a `z3.ModelRef` object returned by `Solver.model` after a call to `Solver.check` that returned `z3.sat`), and returns a `tinyscript.State` object that encodes assignments to the variables as determined by the model.

Additionally, the starter code contains several routines for testing your solution on the sample test cases in the `tests` directory.
* Executing `runtime.py`, `defuse.py`, and `taint.py` from the root of the repository (i.e. **not** from within `src`) will run their respective analyses on all of the cases in `tests`, and print the results to standard output. These results can be compared against the contents of `tests/groundtruth.json`.
* Executing `run_testcases.py` from the root of the repository will run all three checkers against the cases in `tests`, and compute your (hypothetical) score if the grading test suite were identical to the samples in `tests`.

## What to hand in

Submit your work on Gradescope. Create a `zip` archive of the repository, but make sure that you have not included the directory `lab1-2022` at the root of the archive. Additionally, there is no need to hand in test cases or files in `src/__pycache__`, and doing so may slow down processing by the autograder.

You are encouraged to use the `handin.sh` script, which will create an appropriate archive in `handin.zip` to upload to Gradescope. This script will not work when run from Windows' `cmd.exe` or Powershell, but you may translate it to use native Windows commands if you are not already using the WSL2 setup described at the top of this readme.

## Evaluation

This lab is worth 100 points, and will be graded by a combination of autograder test cases and, when necessary, manual inspection by the course staff. The test cases will test the correctness of your implementation by comparing results with our reference implementation. The autograder tests used to assign your final grade will be different than those included in this repository, but will have been randomly generated using the same process.

Each of the checkers is worth 30 points, and documentation is worth 10 points. To receive full credit for documentation, your implementation must provide type annotations on any additional functions that you implement (as illustrated in the starter code), as well as documentation strings at the top of all additional functions that allow the course staff to understand your implementation.

The autograder will assign points to test cases as follows:
* 100% credit if your solution returns `Result.Satisfies` or `Result.Violates`, matching the ground truth.
* 0% credit if your solution returns `Result.Satisfies` or `Result.Violates`, different from the ground truth.
* 50% credit if your solution returns `Result.Unknown` when the ground truth is `Result.Violates`.
* 0% credit if your solution results `Result.Unknown` when the ground truth is `Result.Satisfies`.

If your implementation is unable to run an analysis to completion on all of the test cases (e.g., it raises an exception before returning a `symbolic.Result`), then the course staff will manually inspect your code, and assign partial credit based on our assessed level of completion of the requirements listed in this readme.