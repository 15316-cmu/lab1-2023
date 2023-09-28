from dataclasses import dataclass


@dataclass
class State:
    variables: dict[str, int]


class Token:
    @classmethod
    def parseaction(cls, toks: list):
        new = cls(*toks)
        toks.clear()
        toks.append(new)


class Term(Token):
    pass


@dataclass
class Const(Term):
    value: int

    def __init__(self, value: str) -> 'Const':
        self.value = int(value)


@dataclass
class Var(Term):
    name: str


@dataclass
class Sum(Term):
    left: Term
    right: Term


@dataclass
class Difference(Term):
    left: Term
    right: Term


@dataclass
class Product(Term):
    left: Term
    right: Term


class Formula(Token):
    pass


@dataclass
class TrueC(Formula):
    pass


@dataclass
class FalseC(Formula):
    pass


@dataclass
class NotF(Formula):
    q: Formula


@dataclass
class AndF(Formula):
    p: Formula
    q: Formula


@dataclass
class OrF(Formula):
    p: Formula
    q: Formula


@dataclass
class ImpliesF(Formula):
    p: Formula
    q: Formula


@dataclass
class EqF(Formula):
    left: Term
    right: Term


@dataclass
class LtF(Formula):
    left: Term
    right: Term


class Prog(Token):
    pass

@dataclass
class Skip(Prog):
    pass

@dataclass
class Asgn(Prog):
    name: str
    exp: Term

@dataclass
class Seq(Prog):
    alpha: Prog
    beta: Prog

@dataclass
class If(Prog):
    q: Formula
    alpha: Prog
    beta: Prog

@dataclass
class While(Prog):
    q: Formula
    alpha: Prog

@dataclass
class Output(Prog):
    e: Term

@dataclass
class Abort(Prog):
    pass