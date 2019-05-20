#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Let's test the combinators in a real world application!

@author: lbo
"""

from combinators import *


def Parens():
    """Parentheses contain a term."""
    return (Operator('(') + Term() + Operator(')')) >> (lambda l: l[1])

def Variable():
    """A variable consists of several letters."""
    return (Skip(Whitespace()) + Regex('[a-zA-Z]+[0-9]*'))

def Atom():
    """An atom is a variable or a float or a parentheses term."""
    return (Variable() | Parens() | (Skip(Whitespace()) + Float()))

def Operator(set):
    """An operator or parenthesis."""
    return Last(Skip(Whitespace()) + OneOf(set))

def operator_result_to_tuple(l):
    if len(l) == 1:
        return l[0]
    elif len(l) == 3:
        return tuple(l)
    else:
        # Parse failed if not either 1 or 3.
        raise Exception("Parse failed: Missing operand")

def Power():
    return (OptimisticSequence(Last(Atom()), Operator('^') + Atom()) >> operator_result_to_tuple)

class Product(Parser):

    def parse(self, st):
        # Try to parse an atom, a product operator, and another product.
        p = OptimisticSequence(Power(), Operator('*/') + Product()) >> operator_result_to_tuple
        return p.parse(st)

class Term(Parser):

    def parse(self, st):
        # Try to parse a product, then a sum operator, then another term.
        # OptimisticSequence will just return a product if there is no sum operator.
        p = OptimisticSequence(Product(), Operator('+-') + Term()) >> operator_result_to_tuple
        return p.parse(st)

def pretty_print(tpl):
    # tpl is a (left, op, right) tuple or a scalar.
    if not isinstance(tpl, tuple):
        return str(tpl)
    assert len(tpl) == 3
    return '({} {} {})'.format(pretty_print(tpl[0]), tpl[1], pretty_print(tpl[2]))

def parse_and_print(expr):
    """Parse an expression string and return a string of the parsing result."""
    parsed, st = Term().parse(ps(expr))
    if parsed is None:
        print('Parse error :(', st)
        return
    print(pretty_print(parsed))