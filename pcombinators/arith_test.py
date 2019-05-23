#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Let's test the combinators in a real world application!

@author: lbo
"""

from pcombinators.state import ParseState
from pcombinators.combinators import *
from pcombinators.primitives import *

def Parens():
    """Parentheses contain a term."""
    return (Operator('(') + Term() + Operator(')')) >> (lambda l: l[1])

def Variable():
    """A variable consists of several letters."""
    return Regex('[a-zA-Z]+[0-9]*')

def Atom():
    """An atom is a variable or a float or a parentheses term."""
    return (Variable() | Parens() | Float())

atom = Atom()

def Operator(set):
    """An operator or parenthesis."""
    return OneOf(set)

def operator_result_to_tuple(l):
    if len(l) == 1:
        return l[0]
    elif len(l) == 2 and len(l[1]) == 2:
        return (l[0], l[1][0], l[1][1])
    else:
        # Parse failed if not either 1 or 3.
        raise Exception("Parse failed: Missing operand")

class Power(Parser):
    ops = Operator('^')
    p = OptimisticSequence(atom, Power.ops + power) >> operator_result_to_tuple
    def parse(self, st):
        return self.p.parse(st)

power = Power()

class Product(Parser):
    ops = Operator('*/')
    p = OptimisticSequence(power, Product.ops + product) >> operator_result_to_tuple
    def parse(self, st):
        # Try to parse an atom, a product operator, and another product.
        return self.p.parse(st)

product = Product()

class Term(Parser):
    ops = Operator('+-')
    p = OptimisticSequence(product, Term.ops + term) >> operator_result_to_tuple
    def parse(self, st):
        # Try to parse a product, then a sum operator, then another term.
        # OptimisticSequence will just return a product if there is no sum operator.
        return self.p.parse(st)

term = Term()

def pretty_print(tpl):
    # tpl is a (left, op, right) tuple or a scalar.
    if not isinstance(tpl, tuple):
        return str(tpl)
    assert len(tpl) == 3
    return '({} {} {})'.format(pretty_print(tpl[0]), tpl[1], pretty_print(tpl[2]))

def parse_and_print(expr):
    """Parse an expression string and return a string of the parsing result."""
    parsed, st = Term().parse(ParseState(expr.replace(' ', '')))
    if parsed is None:
        print('Parse error :(', st)
        return
    return pretty_print(parsed)