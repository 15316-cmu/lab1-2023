from functools import reduce
from typing import Optional
import tinyscript as tn
import z3

def unique(func):
    """
    Decorator to make items in a list unique
    """
    def simplifyInner(*args, **kwargs):
        return reduce(
    		lambda l, x: l.append(x) or l if x not in l else l, 
    		func(*args, **kwargs), 
    		[])
    return simplifyInner

def simplify(func):
    """
    Decorator to simplify functions returning z3 values
    """
    def simplifyInner(*args, **kwargs):
        return z3.simplify(func(*args, **kwargs))
    return simplifyInner

def check_sat(
	ps: list[z3.BoolRef],
	timeout: int=None
) -> tuple[z3.CheckSatResult, Optional[z3.ModelRef]]:
	"""
	Checks a list of formulas for satisfiability, with
	an optional timeout.
	
	Args:
	    ps (list[z3.BoolRef]): Formulas to check
	    timeout (int, optional): Timeout in seconds, or `None`
	    	for no timeout. Defaults to `None`.
	
	Returns:
	    tuple[z3.CheckSatResult, Optional[z3.ModelRef]]: If
	    	the conjunction of `ps` is satisfiable, then a tuple
	    	with a corresponding model in the second position.
	    	Otherwise, the second position is `None`.
	"""
	s = z3.Solver()
	if timeout is not None:
		s.set(timeout=int(timeout*1000))
	for p in ps:
		s.add(p)
	res = s.check()
	return (res, s.model() if res == z3.sat else None)

@simplify
def term_enc(e: tn.Term) -> z3.IntNumRef:
    """
    Encode a tinyscript.Term as a z3.IntNumRef
    
    Args:
        e (tn.Term): Term to encode
    
    Returns:
        z3.IntNumRef: Encoded term
    
    Raises:
        TypeError: If the argument isn't a valid 
        	tinyscript term.
    """
    match e:
        case tn.Const(val):
            return z3.IntVal(val)
        case tn.Var(id):
            return z3.Int(id)
        case tn.Sum(left, right):
            return term_enc(left) + term_enc(right)
        case tn.Difference(left, right):
            return term_enc(left) - term_enc(right)
        case tn.Product(left, right):
            return term_enc(left) * term_enc(right)
        case _:
            raise TypeError(
                f"term_enc got {type(e)} ({e}), not Term"
            )


@simplify
def fmla_enc(p: tn.Formula) -> z3.BoolRef:
    """
    Encode a tinyscript.Formula as a z3.BoolRef
    
    Args:
        p (tn.Formula): Formula to encode
    
    Returns:
        z3.BoolRef: Encoded formula
    
    Raises:
        TypeError: If the argument isn't a valid 
        	tinyscript formula.
    """
    match p:
        case tn.TrueC():
            return z3.BoolVal(True)
        case tn.FalseC():
            return z3.BoolVal(False)
        case tn.NotF(q):
            return z3.Not(fmla_enc(q))
        case tn.AndF(p, q):
            return z3.And(fmla_enc(p), fmla_enc(q))
        case tn.OrF(p, q):
            return z3.Or(fmla_enc(p), fmla_enc(q))
        case tn.ImpliesF(p, q):
            return z3.Implies(fmla_enc(p), fmla_enc(q))
        case tn.EqF(left, right):
            return term_enc(left) == term_enc(right)
        case tn.LtF(left, right):
            return term_enc(left) < term_enc(right)
        case _:
            raise TypeError(
                f"fmla_enc got {type(p)} ({p}), not Formula"
            )

def term_stringify(e: tn.Term) -> str:
    """
    Pretty-print a tinyscript term
    
    Args:
        e (tn.Term): Term to print
    
    Returns:
        str: Pretty-printed term
    
    Raises:
        TypeError: Argument is not a valid tinyscript term
    """
    match e:
        case tn.Const(val):
            return str(val)
        case tn.Var(id):
            return id
        case tn.Sum(left, right):
            return f"({term_stringify(left)})+({term_stringify(right)})"
        case tn.Difference(left, right):
            return f"({term_stringify(left)})-({term_stringify(right)})"
        case tn.Product(left, right):
            return f"({term_stringify(left)})*({term_stringify(right)})"
        case _:
            raise TypeError(
                f"term_stringify got {type(e)} ({e}), not Term"
            )


def fmla_stringify(p: tn.Formula) -> str:
    """
    Pretty-print a tinyscript formula
    
    Args:
        p (tn.Formula): Formula to print
    
    Returns:
        str: Pretty-printed formula
    
    Raises:
        TypeError: If the argument isn't a valid tinyscript formula
    """
    match p:
        case tn.TrueC():
            return "true"
        case tn.FalseC():
            return "false"
        case tn.NotF(q):
            return f"!({fmla_stringify(q)})"
        case tn.AndF(p, q):
            return f"({fmla_stringify(p)})&&({fmla_stringify(q)})"
        case tn.OrF(p, q):
            return f"({fmla_stringify(p)})||({fmla_stringify(q)})"
        case tn.ImpliesF(p, q):
            return f"({fmla_stringify(p)})->({fmla_stringify(q)})"
        case tn.EqF(left, right):
            return f"({term_stringify(left)})==({term_stringify(right)})"
        case tn.LtF(left, right):
            return f"({term_stringify(left)})<({term_stringify(right)})"
        case _:
            raise TypeError(
                f"fmla_stringify got {type(p)} ({p}), not Formula"
            )


def stringify(alpha: tn.Prog, indent=0) -> str:
    """
    Pretty-print a tinyscript program
    
    Args:
        alpha (tn.Prog): Program to print
        indent (int, optional): Starting indentation, defaults to `0`
    
    Returns:
        str: Pretty-printed program
    
    Raises:
        TypeError: If the argument is not a valid tinyscript program
    """
    match alpha:
        case tn.Skip():
            return f"{' '*indent}skip"
        case tn.Asgn(name, aexp):
            return f"{' '*indent}{name} := {term_stringify(aexp)}"
        case tn.Seq(alpha_p, beta_p):
            return f"{stringify(alpha_p, indent)};\n{stringify(beta_p, indent)}"
        case tn.If(p, alpha_p, beta_p):
            return (
                f"{' '*indent}if ({fmla_stringify(p)}) then\n"
                f"{stringify(alpha_p, indent+4)}\n"
                f"{' '*indent}else\n"
                f"{stringify(beta_p, indent+4)}\n"
                f"{' '*indent}endif"
            )
        case tn.While(q, alpha_p):
            return (
                f"{' '*indent}while ({fmla_stringify(q)}) do\n"
                f"{stringify(alpha_p, indent+4)}\n"
                f"{' '*indent}done")
        case tn.Output(e):
            return f"{' '*indent}output {term_stringify(e)}"
        case tn.Abort():
            return f"{' '*indent}abort"
        case _:
            raise TypeError(
                f"stringify got {type(alpha)} ({alpha}), not Prog"
            )

@unique
def vars_term(e: tn.Term) -> list[tn.Var]:
	"""
	Collect the variables appearing in a term
	
	Args:
	    e (tn.Term): Term to collect from
	
	Returns:
	    list[tn.Var]: List of variables in argument
	
	Raises:
	    TypeError: If the argument is not a valid tinyscript term
	"""
	match e:
		case tn.Const(val):
			return []
		case tn.Var(id):
			return [e]
		case tn.Sum(left, right):
			return vars_term(left) + vars_term(right)
		case tn.Difference(left, right):
			return vars_term(left) + vars_term(right)
		case tn.Product(left, right):
			return vars_term(left) + vars_term(right)
		case _:
			raise TypeError(
				f"vars_term got {type(e)} ({e}), not Term"
			)

@unique
def vars_formula(p: tn.Formula) -> list[tn.Var]:
	"""
	Collect the variables appearing in a formula
	
	Args:
	    p (tn.Formula): Formula to collect from
	
	Returns:
	    list[tn.Var]: List of variables in argument
	
	Raises:
	    TypeError: If the argument is not a valid tinyscript formula
	"""
	match p:
		case tn.TrueC():
			return []
		case tn.FalseC():
			return []
		case tn.NotF(q):
			return vars_formula(q)
		case tn.AndF(p, q):
			return vars_formula(p) + vars_formula(q)
		case tn.OrF(p, q):
			return vars_formula(p) + vars_formula(q)
		case tn.ImpliesF(p, q):
			return vars_formula(p) + vars_formula(q)
		case tn.EqF(left, right):
			return vars_term(left) + vars_term(right)
		case tn.LtF(left, right):
			return vars_term(left) + vars_term(right)
		case _:
			raise TypeError(
				f"vars_formula got {type(p)} ({p}), not Formula"
			)

@unique
def vars_prog(alpha: tn.Prog) -> list[tn.Var]:
	"""
	Collect the variables appearing in a program
	
	Args:
	    alpha (tn.Prog): Program to collect from
	
	Returns:
	    list[tn.Var]: List of variables in argument
	
	Raises:
	    TypeError: If the argument is not a valid tinyscript program
	"""
	match alpha:
		case tn.Asgn(name, aexp):
			return [tn.Var(name)] + vars_term(aexp)
		case tn.Seq(alpha_p, beta_p):
			return vars_prog(alpha_p) + vars_prog(beta_p)
		case tn.If(p, alpha_p, beta_p):
			return vars_formula(p) + vars_prog(alpha_p) + vars_prog(beta_p)
		case tn.While(q, alpha_p):
			return vars_formula(q) + vars_prog(alpha_p)
		case tn.Output(e):
			return vars_term(e)
		case tn.Skip():
			return []
		case tn.Abort():
			return []
		case _:
			raise TypeError(
				f"vars_prog got {type(alpha)} ({alpha}), not Prog"
			)

def state_from_z3_model(
	alpha: tn.Prog, 
	model: z3.ModelRef,
	complete: bool=True
) -> tn.State:
	"""
	Construct a tinyscript interpreter state from a z3 satisfying
	assignment (model).
	
	Args:
	    alpha (tn.Prog): The program which will run on the returned state
	    model (z3.ModelRef): Model produced by z3.Solver.model() after calling
	    	z3.Solver.check() on satisfiable constraints
	    model_completion (bool, optional): Whether to populate the state with
	    	values for each variable appearing in `alpha`. If set to `False`,
	    	then the state will contain values only for the set of variables
	    	given numeric values in `model`; this may result in runtime
	    	errors if `alpha` is run on the state. Defaults to `True`.
	
	Returns:
	    tn.State: A tinyscript interpreter state which represents the values
	    	determined by `model`.
	"""
	vs = vars_prog(alpha)
	m = lambda x: model.evaluate(z3.Int(x), model_completion=complete)
	state = {
		v.name: m(v.name).as_long() 
		for v in vs
		if isinstance(m(v.name), z3.IntNumRef)
	}
	return tn.State(state)
