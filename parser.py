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
from astnode import StructAccess, SLiteral, Variable, ILiteral, UnaryOp, PointerOp, BinaryOp, Condition, \
        CtrlStatement, RetStatement, StoreStatement, VarDeclStatement, StructStoreStatement, \
        AssignStatement, WhileStatement, IfStatement, BlockStatement, FCallStatement, \
        Func, Struct, Type


class ParserException(Exception):
    def __init__(self, msg, line):
        super().__init__("{}: parser: {}".format(line, msg))


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


def expect(tok, *expects):
    t = tok.next()
    if t in expects:
        return t
    msg = " or ".join(expects)
    raise ParserException("expected {}".format(msg), t.line)

def parse_program(tok):
    structs = []
    funcs = []
    while tok.peek != "eof":
        if tok.peek == "struct":
            s = parse_struct(tok)
            structs.append(s)
        else:
            f = parse_function(tok)
            funcs.append(f)
    return funcs, structs

def parse_struct(tok):
    t = expect(tok, "struct")
    name = expect(tok, "id")
    expect(tok, "{")
    decllist = []
    while tok.peek == "id":
        # member type, member name
        mt, mn = parse_vardecl(tok)
        line = expect(tok, ";").line
        decllist.append(VarDeclStatement(line, type=mt, name=mn))
    expect(tok, "}")
    return Struct(t.line, name=name.value, decls=decllist)

def parse_function(tok):
    ret_type, name = parse_vardecl(tok)
    t = expect(tok, "(")
    arglist = []
    if tok.peek != ")":
        while True:
            tt, p = parse_vardecl(tok)
            arglist.append(VarDeclStatement(t.line, type=tt, name=p))
            if expect(tok, ",", ")") == ")":
                break
    else:
        tok.next()

    # parse function body
    stmt = parse_statement(tok)
    return Func(t.line, type=ret_type, name=name, args=arglist, stmt=stmt)

def parse_vardecl(tok, t = None):
    # doesn't produce a valid ast node!
    if t == None:
        t = expect(tok, "id")
    ptr_count = 0
    while tok.peek == "*":
        ptr_count += 1
        tok.next()
    name = expect(tok, "id")
    return Type(t.line, type=t.value, ptr=ptr_count), name.value

def parse_fcall(tok, t):
    # this doesn't accept normal input!
    # skip over (
    tok.next()
    arglist = []
    if tok.peek != ")":
        while True:
            arg = parse_expression(tok)
            arglist.append(arg)
            if expect(tok, ")", ",") == ")":
                break
    return FCallStatement(t.line, name=t.value, args=arglist)

def parse_block(tok):
    t = expect(tok, "{")
    stmt_list = []
    while tok.peek != "}":
        s = parse_statement(tok)
        if isinstance(s, tuple):
            stmt_list.extend(s)
        else:
            stmt_list.append(s)
    tok.next() # skip }
    return BlockStatement(t.line, stmts=stmt_list)

def parse_if(tok):
    e = None
    t = expect(tok, "if")
    # condition
    c = parse_condition(tok)
    # statement
    s = parse_statement(tok)
    if tok.peek == "else":
        e = parse_statement(tok)
    return IfStatement(t.line, cond=c, statement=s, elsestmt=e)

def parse_while(tok):
    t = expect(tok, "while")
    c = parse_condition(tok)
    s = parse_statement(tok)
    return WhileStatement(t.line, cond=c, statement=s)

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
        return CtrlStatement(t.line, op="break")
    elif tok.peek == "continue":
        t = tok.next()
        expect(tok, ";")
        return CtrlStatement(t.line, op="cont")
    elif tok.peek == "return":
        t = tok.next()
        e = parse_expression(tok)
        expect(tok, ";")
        return RetStatement(t.line, value=e)
    elif tok.peek == "*":
        # memory store
        c = 0
        while tok.peek == "*":
            c += 1
            tok.next()
        f = parse_factor(tok)
        t = expect(tok, "=")
        e = parse_expression(tok)
        expect(tok, ";")
        return StoreStatement(t.line, count=c, ptr=f, value=e)
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
            
            decl = VarDeclStatement(i.line, type=t, name=name)
            assign = AssignStatement(i.line, var=name, value=init)
            return decl, assign
        elif tok.peek == "(":
            # function call
            f = parse_fcall(tok, i)
            expect(tok, ";")
            return f
        else:
            # assignment or error
            s = i.value
            struct = False
            if tok.peek == ".":
                s = parse_struct_access(tok, i)
                # stuct member store
                struct = True
            t = expect(tok, "=")
            e = parse_expression(tok)
            expect(tok, ";")
            if struct:
                return StructStoreStatement(t.line, struct=s, value=e)
            else:
                return AssignStatement(t.line, var=s, value=e)

def parse_condition(tok):
    ops = ("==", "!=", "<=", ">=", "<", ">")
    left = parse_expression(tok)
    op = expect(tok, *(ops))
    right = parse_expression(tok)
    return Condition(op.line, op=op.type, left=left, right=right)

def parse_expression(tok):
    ops = ("+", "-")
    ret = parse_mult(tok)
    while tok.peek.type in ops:
        t = tok.next()
        right = parse_mult(tok)
        ret = BinaryOp(t.line, op=t.type, left=ret, right=right)
    return ret

def parse_mult(tok):
    ops = ("*", "/")
    ret = parse_shift(tok)
    while tok.peek.type in ops:
        t = tok.next()
        right = parse_shift(tok)
        ret = BinaryOp(t.line, op=t.type, left=ret, right=right)
    return ret

def parse_shift(tok):
    ops = (">>>", ">>", "<<")
    ret = parse_bitwise(tok)
    while tok.peek.type in ops:
        t = tok.next()
        right = parse_unary(tok)
        ret = BinaryOp(t.line, op=t.type, left=ret, right=right)
    return ret

def parse_bitwise(tok):
    ops = ("&", "|", "^")
    ret = parse_unary(tok)
    while tok.peek.type in ops:
        t = tok.next()
        right = parse_unary(tok)
        ret = BinaryOp(t.line, op=t.type, left=ret, right=right)
    return ret

def parse_unary(tok):
    ops = ("-", "~", "*", "&", "sizeof")
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
    if t in ("*", "&", "sizeof"):
        return PointerOp(t.line, op=t.type, right=f, ptr=count)
    else:
        return UnaryOp(t.line, op=t.type, right=f)

def parse_factor(tok):
    t = tok.next()
    if t == "(":
        node = parse_expression(tok)
        expect(tok, ")")
        return node
    elif t == "int":
        return ILiteral(t.line, value=t.value)
    elif t == "id":
        if tok.peek == "(":
            return parse_fcall(tok, t)
        elif tok.peek == ".":
            return parse_struct_access(tok, t)
        else:
            return Variable(t.line, name=t.value)
    elif t == "str":
        return SLiteral(t.line, value=t.value)
    else:
        raise ParserException("expected a factor", t.line)

def parse_struct_access(tok, t):
    # struct member access
    ret = None
    while tok.peek == ".":
        tok.next()
        n = expect(tok, "id")
        if ret is None:
            ret = StructAccess(t.line, left=t.value, right=n.value)
        else:
            # left associative => left recursive tree
            ret = StructAccess(n.line, left=ret, right=n.value)
    return ret

def parse(tokens):
    t = Lookahead(tokens, Token("eof", None, -1))
    return parse_program(t)

