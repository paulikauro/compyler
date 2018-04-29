# parser.py
#
# Copyright (C) 2018 Pauli Kauro
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from lexer import Token

class ParserException(Exception):
    def __init__(self, msg, line):
        super().__init__("parser error on line {}: {}".format(line, msg))


class Lookahead(object):
    def __init__(self, gen, default):
        self.peek = next(gen, default)
        self.gen = gen
        self.default = default

    def next(self, count=1):
        while count > 0:
            a = self.peek
            self.peek = next(self.gen, self.default)
            count -= 1
        return a

ast_nodes = ("sliteral", "variable", "fcall", "iliteral", "neg", "inv", "deref", "addrof", "szof", "band", "bor", "bxor", "sra", "srl", "sll", "add", "sub", "eq", "ne", "lt", "gt", "le", "ge", "assign", "sma", "sms", "store", "vardecl", "ret", "cont", "break", "while", "if", "block", "func", "struct", "root")

def prettify_ast(ast):
    val = "("
    # remove line numbers where necessary
    if len(ast) > 1 and ast[0] in ast_nodes:
        del ast[1]
    for node in ast:
        if isinstance(node, list):
            if not node:
                # empty list
                val += "()"
            else:
                val += prettify_ast(node)
        else:
            val += str(node)
        val += " "
    # remove last space and append a closing paren
    return val[:-1] + ")"

def expect(tok, *expects):
    t = tok.next()
    if t in expects:
        return t
    msg = " or ".join(expects)
    raise ParserException("expected {}".format(msg), t.line)

def parse_program(tok):
    ast = ["root", 0]
    while tok.peek != "eof":
        if tok.peek == "struct":
            s = parse_struct(tok)
            ast.append(s)
        else:
            f = parse_function(tok)
            ast.append(f)
    return ast

def parse_struct(tok):
    t = expect(tok, "struct")
    name = expect(tok, "id")
    expect(tok, "{")
    decllist = []
    while tok.peek == "id":
        # member type, member name
        mt, mn = parse_vardecl(tok)
        expect(tok, ";")
        decllist.append([mt, mn])
    expect(tok, "}")
    return ["struct", t.line, name.value, decllist]

def parse_function(tok):
    ret_type, name = parse_vardecl(tok)
    t = expect(tok, "(")
    ret = ["func", t.line, ret_type, name]
    arglist = []
    if tok.peek != ")":
        while True:
            t, p = parse_vardecl(tok)
            arglist.append([t, p])
            if expect(tok, ",", ")") == ")":
                break
    else:
        tok.next()
    ret.append(arglist)
    # parse function body
    ret.append(parse_statement(tok))
    return ret

def parse_vardecl(tok, t = None):
    # doesn't produce a valid ast node!
    if t == None:
        t = expect(tok, "id")
    ptr = 0
    while tok.peek == "*":
        ptr += 1
        tok.next()
    name = expect(tok, "id")
    return [t.value, ptr], name.value

def parse_fcall(tok, t):
    # this doesn't accept normal input!
    # skip over (
    tok.next()
    node = ["fcall", t.line, t.value]
    arglist = []
    if tok.peek != ")":
        while True:
            arg = parse_expression(tok)
            arglist.append(arg)
            if expect(tok, ")", ",") == ")":
                break
    node.append(arglist)
    return node

def parse_block(tok):
    t = expect(tok, "{")
    ret = ["block", t.line]
    while tok.peek != "}":
        ret.append(parse_statement(tok))
    tok.next() # skip }
    return ret

def parse_if(tok):
    # else statement
    e = None
    t = expect(tok, "if")
    # condition
    c = parse_condition(tok)
    # statement
    s = parse_statement(tok)
    if tok.peek == "else":
        e = parse_statement(tok)
    return ["if", t.line, c, s, e]

def parse_while(tok):
    t = expect(tok, "while")
    c = parse_condition(tok)
    s = parse_statement(tok)
    return ["while", t.line, c, s]

def parse_statement(tok):
    if tok.peek == "{":
        return parse_block(tok)
    elif tok.peek == "if":
        return parse_if(tok)
    elif tok.peek == "while":
        return parse_while(tok)
    elif tok.peek == "break":
        t = tok.next()
        expect(tok, ";")
        return ["break", t.line]
    elif tok.peek == "continue":
        t = tok.next()
        expect(tok, ";")
        return ["cont", t.line]
    elif tok.peek == "return":
        t = tok.next()
        e = parse_expression(tok)
        expect(tok, ";")
        return ["ret", t.line, e]
    elif tok.peek == "*":
        # memory store
        ptr = 0
        while tok.peek == "*":
            ptr += 1
            tok.next()
        f = parse_factor(tok)
        t = expect(tok, "=")
        e = parse_expression(tok)
        expect(tok, ";")
        return ["store", t.line, ptr, f, e]
    else:
        # variable declaration, function call or assignment
        i = expect(tok, "id")
        if tok.peek.type in ("id", "*"):
            # variable declaration
            t, name = parse_vardecl(tok, i)
            # no initialization by default
            init = None
            if tok.peek == "=":
                tok.next()
                init = parse_expression(tok)
            expect(tok, ";")
            return ["vardecl", i.line, t, name, init]
        elif tok.peek == "(":
            # function call
            f = parse_fcall(tok, i)
            expect(tok, ";")
            return f
        else:
            # assignment or error
            s = i.value
            nodename = "assign"
            if tok.peek == ".":
                s = parse_struct_access(tok, i)
                # stuct member store
                nodename = "sms"
            t = expect(tok, "=")
            e = parse_expression(tok)
            expect(tok, ";")
            return [nodename, t.line, s, e]

def parse_condition(tok):
    ops = {
        "==": "eq",
        "!=": "ne",
        "<": "lt",
        ">": "gt",
        "<=": "le",
        ">=": "ge"
    }
    ret = parse_expression(tok)
    op = expect(tok, *(ops.keys()))
    return [ops[op.type], tok.peek.line, ret, parse_expression(tok)]

def parse_expression(tok):
    ops = {
        "+": "add",
        "-": "sub"
    }
    ret = parse_mult(tok)
    while tok.peek.type in ops:
        t = tok.next()
        ret = [ops[t.type], t.line, ret, parse_mult(tok)]
    return ret

def parse_mult(tok):
    ops = {
        "*": "mul",
        "/": "div"
    }
    ret = parse_shift(tok)
    while tok.peek.type in ops:
        t = tok.next()
        ret = [ops[t.type], t.line, ret, parse_shift(tok)]
    return ret

def parse_shift(tok):
    ops = {
        ">>>": "sra",
        ">>": "srl",
        "<<": "sll"
    }
    ret = parse_bitwise(tok)
    while tok.peek.type in ops:
        t = tok.next()
        ret = [ops[t.type], t.line, ret, parse_bitwise(tok)]
    return ret

def parse_bitwise(tok):
    ops = {
        "&": "band",
        "|": "bor",
        "^": "bxor"
    }
    ret = parse_unary(tok)
    while tok.peek.type in ops:
        t = tok.next()
        ret = [ops[t.type], t.line, ret, parse_unary(tok)]
    return ret

def parse_unary(tok):
    ops = {
        "-": "neg",
        "~": "inv",
        "*": "deref",
        "&": "addrof",
        "sizeof": "szof"
    }
    if tok.peek.type not in ops:
        return parse_factor(tok)

    t = tok.next()
    count = 1
    while tok.peek == t:
        if t == "sizeof":
            raise ParserException("sizeof sizeof not supported", t.line)
        count += 1

    if t in ("-", "~") and count % 2 == 0:
        # double inversion, double negation cancel out
        return parse_factor(tok)

    f = parse_factor(tok)
    ret = [ops[t.type], t.line, f]
    if t in ("*", "&"):
        ret.insert(2, count)
    return ret

def parse_factor(tok):
    t = tok.next()
    if t == "(":
        node = parse_expression(tok)
        expect(tok, ")")
        return node
    elif t == "int":
        return ["iliteral", t.line, t.value]
    elif t == "id":
        if tok.peek == "(":
            return parse_fcall(tok, t)
        elif tok.peek == ".":
            return parse_struct_access(tok, t)
        else:
            return ["variable", t.line, t.value]
    elif t == "str":
        return ["sliteral", t.line, t.value]
    else:
        raise ParserException("expected a factor", t.line)

def parse_struct_access(tok, t):
    # struct member access
    ret = None
    while tok.peek == ".":
        tok.next()
        n = expect(tok, "id")
        if ret == None:
            ret = ["sma", t.line, t.value, n.value]
        else:
            # left associative => left recursive tree
            ret = ["sma", n.line, ret, n.value]
    return ret

def parse(tokens):
    t = Lookahead(tokens, Token("eof", None, -1))
    return parse_program(t)

