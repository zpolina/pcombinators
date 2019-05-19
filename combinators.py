#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser combinators losely inspired by Haskell's monadic parsers.

The monad here is the result tuple (result, ParseState), which is returned
by all Parser's parse() method.
"""

import re

class Util:
    def extend_results(a, e):
        if isinstance(e, list):
            a.extend(e)
        else:
            a.append(e)
        return a

def ps(s):
    return ParseState(s)

class ParseState:
    """Encapsulates state as the parser goes through input."""

    _input = ''
    _index = 0

    def __init__(self, s):
        self._input = s

    def __repr__(self):
        if self._index < len(self._input):
            return 'ParseState({}< {} >{})'.format(
                    self._input[0:self._index], self._input[self._index], self._input[self._index+1:])
        else:
            return 'ParseState({}<>)'.format(self._input)

    def next(self):
        current = self.peek()
        self._index += 1
        return current

    def peek(self):
        return self._input[self._index]

    def index(self):
        return self._index

    def reset(self, ix):
        self._index = ix

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def finished(self):
        return self._index == len(self._input)

    def remaining(self):
        if self.finished():
            return ''
        return self._input[self._index:]

class Parser:
    """Super class for all parsers. Implements operator overloading for easier
    chaining of parsers."""
    type = None

    def parse(self, st):
        return (None, st)

    def __add__(self, other):
        """Chain parsers, only match if all match in sequence."""
        return AtomicSequence(self, other)

    def __mul__(self, times):
        """Repeat a parser exactly `times`."""
        return StrictRepeat(self, times)

    def __rmul__(self, times):
        """Repeat a parser exactly `times`."""
        return self.__mul__(times)

    def __or__(self, other):
        """Chain parsers as alternatives (first-match)."""
        return FirstAlternative(self, other)

    def __rshift__(self, fn):
        """Transform the result of a parser using an unary function.

        Example:
            Regex('[a-z]+') >> (lambda s: s[0])

            consumes all lower case characters but results in only the first.

            Regex('\d+') >> int >> (lambda i: i*2)

            consume digits and convert them to an integer, multiplying it by two..
        """
        return _Transform(self, fn)

    def then(self, next):
        """Consume part of the input, discarding it, and return the result
        parsed by the supplied next parser."""
        return Last(AtomicSequence(self, next))

# Combinators

class _Transform(Parser):
    _inner = None
    _transform = lambda x: x

    def __init__(self, inner, tf):
        self._inner = inner
        self._transform = tf

    def parse(self, st):
        initial = st.index()
        r, st2 = self._inner.parse(st)
        if r is None:
            st.reset(initial)
            return None, st
        try:
            return self._transform(r), st2
        except Exception as e:
            st.reset(initial)
            raise Exception('{} (at {} (col {}))'.format(e, st, st.index()))

class _Sequence(Parser):
    _parsers = []
    _atomic = None

    def __init__(self, *parsers):
        self._parsers = parsers

    def parse(self, st):
        results = []
        initial = st.index()
        for p in self._parsers:
            before = st.index()
            result, st2 = p.parse(st)
            if result is None:
                if self._atomic:
                    st.reset(initial)
                    return None, st
                st.reset(before)
                break
            Util.extend_results(results, result)
            st = st2
        return results, st2


class AtomicSequence(_Sequence):
    """Execute a series of parsers after each other. All must succeed. Result is list of results of the parsers."""
    _atomic = True

class OptimisticSequence(_Sequence):
    """Execute a series of parsers after each other, as far as possible
    (until the first parser fails). Result is list of results of the parsers."""
    _atomic = False

class _Repeat(Parser):
    _parser = None
    _times = 0
    _strict = None

    def __init__(self, parser, repeat):
        self._parser = parser
        self._times = repeat

    def parse(self, st):
        results = []
        initial = st.index()
        i = 0

        while i < self._times or self._times < 0:
            r, st2 = self._parser.parse(st)
            if r == None:
                if self._strict:
                    st.reset(initial)
                    return None, st
                return results, st2
            Util.extend_results(results, r)
            st = st2
            i += 1
        return results, st

class StrictRepeat(_Repeat):
    """Expect exactly `repeat` matches of a parser. Result is list of results of the parsers."""
    _strict = True

class Repeat(_Repeat):
    """Expect up to `repeat` matches of a parser. -1 means indefinitely many matches.
    Result is list of results of the parsers."""
    _strict = False

def Maybe(p):
    return Repeat(p, 1)

class _Alternative(Parser):
    """Attempt a series of parsers and return the result of the first one matching."""
    _parsers = []
    _longest = None

    def __init__(self, *parsers):
        self._parsers = parsers

class FirstAlternative(_Alternative):
    """Attempt parsers until one matches. Result is result of that parser."""

    def parse(self, st):
        initial = st.index()
        for p in self._parsers:
            r, st2 = p.parse(st)
            if r is not None:
                return r, st2
            st.reset(initial)
        return None, st

class LongestAlternative(_Alternative):
    """Attempt all parsers and return the longest match. Result is result of best parser."""

    def parse(self, st):
        matches = []
        initial = st.index()
        for p in self._parsers:
            r, st2 = p.parse(st)
            if r is None:
                st.reset(initial)
                continue
            matches.append((st2.index() - initial, r))
            st = st2
            st.reset(initial)

        if len(matches) == 0:
            st.reset(initial)
            return None, st
        # Stable sort!
        matches.sort(key=lambda t: t[0])
        # Return first element that had longest match.
        matches.reverse()
        best = matches[0]
        for r in matches[1:]:
            if r[0] < best[0]:
                break
            best = r
        st.reset(initial + best[0])
        return best[1], st

# Some combinators can be implemented directly.

def Last(p):
    """Return the last result from the list of results of p. Result is scalar."""
    return p >> (lambda l: l[-1] if isinstance(l, list) else l)

def Skip(p):
    """Omit the result of parser p, and replace it with []. Result is []."""
    return p >> (lambda r: [])

def ConcatenateResults(p):
    """Concatenate string results into a single string. Result is string."""
    return p >> (lambda l: ''.join(l) if l and len(l) > 0 else None)

# Parsers

class String(Parser):
    """Consume a fixed string. Result is the string."""
    _s = ''

    def __init__(self, s):
        self._s = s

    def parse(self, st):
        initial = st.index()
        s = self._s
        i = 0
        while i < len(s) and not st.finished() and s[i] == st.peek():
            st.next()
            i += 1
        if i == len(s):
            return (self._s, st)
        st.reset(initial)
        return (None, st)

class OneOf(Parser):
    """Parse characters in the given set. Result is string or None, if none were parsed."""
    _set = None

    def __init__(self, s):
        """
        Example:
            CharSet('abcd')
            CharSet('0123456789')
        """
        self._set = set(s)

    def parse(self, st):
        if not st.finished() and st.peek() in self._set:
            return st.next(), st
        else:
            return None, st


class Regex(Parser):
    """Parse a string using a regular expression. The result is either the
    string or a tuple with all matched groups. Result is string."""
    _rx = None

    def __init__(self, rx):
        if not isinstance(rx, re.Pattern):
            rx = re.compile(rx)
        self._rx = rx

    def parse(self, st):
        start = st.index()
        match = re.match(self._rx, st.remaining())
        if match is None:
            return None, st
        begin, end = match.span()
        result = match.group(0)
        if len(match.groups()) > 1:
            result = list(match.groups())
        elif len(match.groups()) > 0:
            result = match.group(1)
        st.reset(start+end)
        return result, st

# Small specific parsers.

def Nothing():
    """Matches the empty string, and always succeeds."""
    return String('')

def CharSet(s):
    """Matches arbitrarily many characters from the set s (which can be a string).
    Result is string."""
    return ConcatenateResults(Repeat(OneOf(s), -1))

# See section below for optimized versions of the following parsers.

def CanonicalInteger():
    """Return a parser that parses integers and results in an integer. Result is int."""
    return Last(Whitespace() + (ConcatenateResults(Maybe(String('-')) + CharSet('0123456789')) >> int))

def CanonicalFloat():
    """Return a parser that parses floats and results in floats. Result is float."""
    def c(l):
        """Convert parts of a number into a float."""
        if l and len(l) > 0:
            return float(''.join(l))
        return None
    number = OptimisticSequence(
            Repeat(OneOf('-'), 1) + CharSet('0123456789'),
            Repeat(OneOf('.'), 1) + CharSet('0123456789'))
    return (Skip(Whitespace()) + number) >> c

def NonEmptyString():
    """Return a parser that parses a string until the first whitespace,
    skipping whitespace before. Result is string."""
    return Last(Whitespace() + Regex('\w+'))

def Whitespace():
    """Parse whitespace (space, newline, tab). Result is string."""
    return CharSet(' \n\r\t') | Nothing()

# Optimized parsers

class Float():
    """Parses a float like [-]ddd[.ddd].

    Float parses floats with more manual code, making it up to 40% faster than
    CanonicalFloat."""
    _digits = CharSet('0123456789')

    def parse(self, st):
        initial = st.index()
        multiplier = 1
        minus, st = String('-').parse(st)
        if minus is not None:
            multiplier = -1
        big, st = self._digits.parse(st)
        if big is None:
            st.reset(initial)
            return None, st
        small = ''
        dot, st = String('.').parse(st)
        if dot is not None:
            small, st = self._digits.parse(st)
            if small is not None:
                return float(big + '.' + small) * multiplier, st
        return float(big) * multiplier, st

class Integer():
    """Parser for integers of form [-]dddd[...]. Result is int.

    This parser is up to twice as fast as CanonicalInteger and thus implemented
    manually."""
    _digits = CharSet('0123456789')

    def parse(self, st):
        initial = st.index()
        multiplier = 1
        minus, st = String('-').parse(st)
        if minus is not None:
            multiplier = -1
        digits, st = self._digits.parse(st)
        if digits is not None:
            return int(digits)*multiplier, st
        st.reset(initial)
        return None, st