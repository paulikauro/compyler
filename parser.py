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
import astnode as node


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
        member_type, member_name = parse_vardecl(tok)
        line = expect(tok, ";").line
        decl = node.VarDeclStatement(line, type=member_type, name=member_name)
        decllist.append(decl)
    expect(tok, "}")
    return node.Struct(t.line, name=name.value, decls=decllist)

def parse_function(tok):
    ret_type, name = parse_vardecl(tok)
    t = expect(tok, "(")
    arglist = []
    if tok.peek != ")":
        while True:
            type, name = parse_vardecl(tok)
            arglist.append(node.VarDeclStatement(t.line, type=type, name=name))
            if expect(tok, ",", ")") == ")":
                break
    else:
        tok.next()

    # parse function body
    stmt = parse_statement(tok)
    return node.Func(t.line, type=ret_type, name=name, args=arglist, stmt=stmt)

def parse_vardecl(tok, t = None):
    # doesn't produce a valid ast node!
    if t == None:
        t = expect(tok, "id")
    ptr_level = 0
    while tok.peek == "*":
        ptr_level += 1
        tok.next()
    name = expect(tok, "id")
    return node.Type(t.line, type=t.value, level=ptr_level), name.value

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
    return node.FCallStatement(t.line, name=t.value, args=arglist)

def parse_block(tok):
    t = expect(tok, "{")
    stmt_list = []
    while tok.peek != "}":
        s = parse_statement(tok)
        if isinstance(s, tuple):
            # in case multiple statements are returned
            stmt_list.extend(s)
        else:
            stmt_list.append(s)
    tok.next() # skip }
    return node.BlockStatement(t.line, stmts=stmt_list)

def parse_if(tok):
    else_body = None
    t = expect(tok, "if")
    cond = parse_condition(tok)
    body = parse_statement(tok)
    if tok.peek == "else":
        else_body = parse_statement(tok)
    return node.IfStatement(t.line, cond=cond, stmt=body, elsestmt=else_body)

def parse_while(tok):
    t = expect(tok, "while")
    cond = parse_condition(tok)
    body = parse_statement(tok)
    return node.WhileStatement(t.line, cond=cond, stmt=body)

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
        return node.CtrlStatement(t.line, op="break")
    elif tok.peek == "continue":
        t = tok.next()
        expect(tok, ";")
        return node.CtrlStatement(t.line, op="cont")
    elif tok.peek == "return":
        t = tok.next()
        expr = parse_expression(tok)
        expect(tok, ";")
        return node.RetStatement(t.line, value=expr)
    elif tok.peek == "*":
        # memory store
        ptr_level = 0
        while tok.peek == "*":
            ptr_level += 1
            tok.next()
        factor = parse_factor(tok)
        t = expect(tok, "=")
        expr = parse_expression(tok)
        expect(tok, ";")
        return node.StoreStatement(t.line, level=ptr_level, ptr=factor, value=expr)
    else:
        # variable declaration, function call or assignment
        i = expect(tok, "id")
        if tok.peek.type in ("id", "*"):
            # variable declaration
            type, name = parse_vardecl(tok, i)
            # no initialization by default
            assign = None
            if tok.peek == "=":
                tok.next()
                init = parse_expression(tok)
                assign = node.AssignStatement(i.line, var=name, value=init)
            expect(tok, ";")
            
            decl = node.VarDeclStatement(i.line, type=type, name=name)
            if assign: return decl, assign
            return decl
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
            expr = parse_expression(tok)
            expect(tok, ";")
            if struct:
                return node.StructStoreStatement(t.line, struct=s, value=expr)
            else:
                return node.AssignStatement(t.line, var=s, value=expr)

def parse_condition(tok):
    ops = ("==", "!=", "<=", ">=", "<", ">")
    left = parse_expression(tok)
    op = expect(tok, *(ops))
    right = parse_expression(tok)
    return node.Condition(op.line, op=op.type, left=left, right=right)

def parse_expression(tok):
    ops = ("+", "-")
    ret = parse_mult(tok)
    while tok.peek.type in ops:
        t = tok.next()
        right = parse_mult(tok)
        ret = node.BinaryOp(t.line, op=t.type, left=ret, right=right)
    return ret

def parse_mult(tok):
    ops = ("*", "/")
    ret = parse_shift(tok)
    while tok.peek.type in ops:
        t = tok.next()
        right = parse_shift(tok)
        ret = node.BinaryOp(t.line, op=t.type, left=ret, right=right)
    return ret

def parse_shift(tok):
    ops = (">>>", ">>", "<<")
    ret = parse_bitwise(tok)
    while tok.peek.type in ops:
        t = tok.next()
        right = parse_unary(tok)
        ret = node.BinaryOp(t.line, op=t.type, left=ret, right=right)
    return ret

def parse_bitwise(tok):
    ops = ("&", "|", "^")
    ret = parse_unary(tok)
    while tok.peek.type in ops:
        t = tok.next()
        right = parse_unary(tok)
        ret = node.BinaryOp(t.line, op=t.type, left=ret, right=right)
    return ret

def parse_unary(tok):
    ops = ("-", "~", "*", "&", "sizeof")
    if tok.peek.type not in ops:
        return parse_factor(tok)

    t = tok.next()
    level = 1
    while tok.peek == t:
        if t == "sizeof":
            raise ParserException("sizeof sizeof not supported", t.line)
        level += 1

    if t in ("-", "~") and level % 2 == 0:
        # double inversion, double negation cancel out
        return parse_factor(tok)

    factor = parse_factor(tok)
    if t in ("*", "&", "sizeof"):
        return node.PointerOp(t.line, op=t.type, right=factor, level=level)
    else:
        return node.UnaryOp(t.line, op=t.type, right=factor)

def parse_factor(tok):
    t = tok.next()
    if t == "(":
        expr = parse_expression(tok)
        expect(tok, ")")
        return expr
    elif t == "int":
        return node.ILiteral(t.line, value=t.value)
    elif t == "id":
        if tok.peek == "(":
            return parse_fcall(tok, t)
        elif tok.peek == ".":
            return parse_struct_access(tok, t)
        else:
            return node.Variable(t.line, name=t.value)
    elif t == "str":
        return node.SLiteral(t.line, value=t.value)
    else:
        raise ParserException("expected a factor", t.line)

def parse_struct_access(tok, t):
    # struct member access
    ret = None
    while tok.peek == ".":
        tok.next()
        n = expect(tok, "id")
        if ret is None:
            ret = node.StructAccess(t.line, left=t.value, right=n.value)
        else:
            # left associative => left recursive tree
            ret = node.StructAccess(n.line, left=ret, right=n.value)
    return ret

def parse(tokens):
    t = Lookahead(tokens, Token("eof", None, -1))
    return parse_program(t)

