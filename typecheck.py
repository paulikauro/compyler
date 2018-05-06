# typecheck.py: type & scope checker
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

from functools import singledispatch
from copy import copy
import astnode


class SemanticsException(Exception):
    def __init__(self, line, *msg):
        super().__init__("{}: semantics: {}".format(line, "".join(msg)))

builtin_types = {"u0": 0,
    "u8": 1, "u16": 2, "u32": 4, "u64": 8,
    "i8": 1, "i16": 2, "i32": 4, "i64": 8}
pointer_size = 8

def check_structs(structs):
    struct_names = [s.name for s in structs]
    struct_dict = {name: struct for name, struct in zip(struct_names, structs)}
    for struct in structs:
        check(struct, struct_dict)
    return struct_dict

def check_funcs(funcs, structs):
    for func in funcs:
        check(func, funcs, structs)

@singledispatch
def check(node, *args):
    print("Generic check function, type", node.__class__.__name__)
    print("Node is", node)
    print("My arguments are", args)

def expand_struct(struct, structs, scope=set(), size=0):
    """Expands a struct definition and checks for recursive definitions."""
    newdecls = []
    scope.add(struct.name)
    for decl in struct.decls:
        decl.soffset = size
        if decl.type.type in scope:
            raise SemanticsException(decl.line, "recursive struct definition")
        elif decl.type.level > 0:
            size += pointer_size
            newdecls.append(copy(decl))
            continue
        elif decl.type.type in builtin_types:
            size += builtin_types[decl.type.type]
            newdecls.append(copy(decl))
        elif decl.type.type in structs:
            size, fields = expand_struct(structs[decl.type.type], structs, scope, size)
            # correct names
            for field in fields:
                field.name = decl.name + "." + field.name
            newdecls.extend(fields)
        else:
            # also in vardecl
            raise SemanticsException(decl.line,
                "type ", decl.type.type, " not found")
    scope.remove(struct.name)
    return size, newdecls

@check.register(astnode.Struct)
def check_struct(struct, structs):
    """Checks for duplicate member names and performs type checking."""
    names = set()
    for decl in struct.decls:
        if decl.name in names:
            raise SemanticExeception(decl.line,
                "struct member ", decl.name, " defined twice")
        names.add(decl.name)
        check(decl, structs)

    struct.size, fields = expand_struct(struct, structs)
    # set the expanded fields
    struct.decls = fields

@check.register(astnode.VarDeclStatement)
def check_vardecl(decl, structs):
    """Checks for undefined types."""
    if not (decl.type.type in structs or decl.type.type in builtin_types):
        raise SemanticsException(decl.line,
            "type ", decl.type.type, " not found")



