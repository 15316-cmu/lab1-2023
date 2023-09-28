#!/usr/bin/env python3

import tinyscript as tn
from typing import Optional
from tinyscript_util import fmla_stringify
from enum import Enum

Status = Enum('Status', ['Terminated', 'Aborted', 'Error', 'Maxsteps'])

def term_exc(state: tn.State, aexp: tn.Term) -> int:
    match aexp:
        case tn.Const(val):
            return val
        case tn.Var(name):
            if name not in state.variables:
                raise RuntimeError(
                    f"Variable {name} undefined in state {state}")
            return state.variables[name]
        case tn.Sum(left, right):
            return term_exc(state, left) + term_exc(state, right)
        case tn.Difference(left, right):
            return term_exc(state, left) - term_exc(state, right)
        case tn.Product(left, right):
            return term_exc(state, left) * term_exc(state, right)
        case _:
            raise TypeError(
                f"term_exc got {type(aexp)} ({aexp}), not Term"
            )


def fmla_exc(state: tn.State, bexp: tn.Formula) -> bool:
    match bexp:
        case tn.TrueC():
            return True
        case tn.FalseC():
            return False
        case tn.NotF(q):
            return not fmla_exc(state, q)
        case tn.AndF(p, q):
            return fmla_exc(state, p) and fmla_exc(state, q)
        case tn.OrF(p, q):
            return fmla_exc(state, p) or fmla_exc(state, q)
        case tn.ImpliesF(p, q):
            return (not fmla_exc(state, p)) or fmla_exc(state, q)
        case tn.EqF(left, right):
            return term_exc(state, left) == term_exc(state, right)
        case tn.LtF(left, right):
            return term_exc(state, left) < term_exc(state, right)
        case _:
            raise TypeError(
                f"fmla_exc got {type(bexp)} ({bexp}), not Formula"
            )


def exc(
    state: tn.State,
    alpha: tn.Prog,
    max_steps: int=None,
    quiet: bool=False
) -> tuple[tn.State, Status, int]:
    """
    Execute a TinyScript program.

    Args:
        state (tn.State): initial state
        alpha (tn.Prog): program to execute
        max_steps (int, optional): maximum number of steps to execute
        quiet (bool, optional): if True, don't print interpreter errors

    Returns:
        tuple[tn.State, Status, int]: final state, final status, # steps remaining
    """
    if max_steps == 0:
        print("we're 0!")
        return (state, Status.Maxsteps, 0)
    match alpha:
        case tn.Skip():
            return (
                state, 
                Status.Terminated, 
                max_steps-1 if max_steps is not None else None)
        case tn.Asgn(name, e):
            try:
                e_val = term_exc(state, e)
            except BaseException as e:
                if not quiet:
                    print('Interpreter Error:', str(e))
                return (state, Status.Error, max_steps)
            return (
                tn.State(state.variables | {name: e_val}),
                Status.Terminated,
                max_steps-1 if max_steps is not None else None)
        case tn.Seq(alpha_p, beta_p):
            o1 = exc(state, alpha_p, max_steps, quiet)
            match o1[1]:
                case Status.Maxsteps|Status.Aborted|Status.Error:
                    return o1
                case Status.Terminated:
                    return exc(o1[0], beta_p, o1[2], quiet)
        case tn.If(q, alpha_p, beta_p):
            try:
                q_val = fmla_exc(state, q)
            except BaseException as e:
                if not quiet:
                    print('Interpreter Error:', str(e))
                return (state, Status.Error, max_steps)
            if q_val:
                return exc(state, alpha_p, max_steps, quiet)
            else:
                return exc(state, beta_p, max_steps, quiet)
        case tn.While(q, alpha_p):
            while max_steps is None or max_steps > 0:
                try:
                    q_val = fmla_exc(state, q)
                except BaseException as e:
                    if not quiet:
                        print('Interpreter Error:', str(e))
                    return (state, Status.Error, max_steps)
                if not q_val:
                    return (state, Status.Terminated, max_steps)
                state = exc(state, alpha_p, max_steps, quiet)
                match state[1]:
                    case Status.Maxsteps|Status.Aborted|Status.Error:
                        return state
                if state[2] == 0:
                    return (state[0], Status.Maxsteps, 0)
                if max_steps is not None:
                    max_steps = min(state[2], max_steps-1)
                state = state[0]
            return (state, Status.Maxsteps)
        case tn.Output(e):
            try:
                e_val = term_exc(state, e)
            except BaseException as e:
                if not quiet:
                    print('Interpreter Error:', str(e))
                return (state, Status.Error, max_steps)
            return (
                tn.State(state.variables | {'#stdout': e_val}),
                Status.Terminated,
                max_steps-1 if max_steps is not None else None)
        case tn.Abort():
            return (
                state, 
                Status.Aborted, 
                max_steps-1 if max_steps is not None else None)
        case _:
            raise TypeError(
                f"exc got {type(alpha)} ({alpha}), not Prog"
            )


if __name__ == "__main__":
    import sys
    from parser import parse
    from tinyscript_util import stringify
    with open(sys.argv[1], 'r') as f:
        prog = parse(f.read())
        print(stringify(prog))
        print(exc(tn.State({}), prog))
