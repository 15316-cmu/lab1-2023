#!/usr/bin/env python3

from functools import lru_cache
from pyparsing import (
    Regex,
    Word,
    Forward,
    Suppress,
    alphas,
    alphanums,
)
import tinyscript as tn


def IdentParser():
    return Word(alphas+'#', alphanums+'_')


@lru_cache
def TermParser():
    term = Forward()

    const = Regex(r"-?\d+").set_parse_action(tn.Const.parseaction)
    ident = IdentParser().set_parse_action(tn.Var.parseaction)
    lpar, rpar = map(Suppress, "()")
    paren = lpar + term + rpar

    plus, minus, times = map(Suppress, "+-*")

    atom = const | ident | paren
    times_term = Forward()
    times_term <<= atom \
        ^ (times_term + times + atom).set_parse_action(tn.Product.parseaction)
    term <<= times_term \
        ^ (term + plus + times_term).set_parse_action(tn.Sum.parseaction) \
        ^ (term + minus + times_term).set_parse_action(tn.Difference.parseaction)

    term.enable_left_recursion()
    return term


@lru_cache
def FormulaParser():
    term = TermParser()
    fmla = Forward()

    true_const = Suppress("true").set_parse_action(tn.TrueC.parseaction)
    false_const = Suppress("false").set_parse_action(tn.FalseC.parseaction)
    lpar, rpar = map(Suppress, "()")
    paren = lpar + fmla + rpar

    eq = (term + Suppress("==") + term).set_parse_action(tn.EqF.parseaction)
    lt = (term + Suppress("<") + term).set_parse_action(tn.LtF.parseaction)

    not_tok, and_tok, or_tok, implies_tok = map(Suppress,
                                                ["!", "&&", "||", "->"])

    atom = true_const | false_const | paren | eq | lt
    not_fmla = atom ^ (not_tok + atom).set_parse_action(tn.NotF.parseaction)
    and_fmla = Forward()
    and_fmla <<= not_fmla \
        ^ (and_fmla + and_tok + not_fmla).set_parse_action(tn.AndF.parseaction)
    or_fmla = Forward()
    or_fmla <<= and_fmla \
        ^ (or_fmla + or_tok + and_fmla).set_parse_action(tn.OrF.parseaction)
    fmla <<= or_fmla \
        ^ (fmla + implies_tok + or_fmla).set_parse_action(
            tn.ImpliesF.parseaction)

    fmla.enable_left_recursion()
    return fmla


@lru_cache
def ProgramParser():
    term = TermParser()
    fmla = FormulaParser()
    prog = Forward()

    lpar, rpar = map(Suppress, "()")
    condition = lpar + fmla + rpar

    assign_prog = (IdentParser() + Suppress(":=") + term).set_parse_action(
        tn.Asgn.parseaction)

    if_prog = (Suppress("if") + condition + Suppress("then") + prog +
               Suppress("else") + prog + Suppress("endif")).set_parse_action(
                   tn.If.parseaction)

    while_prog = (Suppress("while") + condition + Suppress("do") + prog +
                  Suppress("done")).set_parse_action(tn.While.parseaction)

    output_prog = (Suppress("output") + term).set_parse_action(
        tn.Output.parseaction)

    skip_prog = (Suppress("skip")).set_parse_action(tn.Skip.parseaction)

    abort_prog = (Suppress("abort")).set_parse_action(tn.Abort.parseaction)

    statement = assign_prog | if_prog | while_prog | output_prog | skip_prog | abort_prog
    prog <<= statement \
        ^ (
            prog + Suppress(";") + statement
        ).set_parse_action(tn.Seq.parseaction)

    prog.enable_left_recursion()
    return prog


def term_parse(s: str):
    return TermParser().parse_string(s, parse_all=True)[0]


def fmla_parse(s: str):
    return FormulaParser().parse_string(s, parse_all=True)[0]


def parse(s: str):
    return ProgramParser().parse_string(s, parse_all=True)[0]


if __name__ == "__main__":
    global a
    a = term_parse
    global b
    b = fmla_parse
    global p
    p = parse
