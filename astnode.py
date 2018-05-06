# astnode.py: AST node definitions and visitor functions
# "ast" is a standard library module, so astnode was used for this instead
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

class BaseNode: pass

def node(node_type, slots):
    """Creates a new node type object."""
    def node_init(self, line, **values):
        """A generic initializer for the nodes."""
        self.line = line
        # __slots__ instead of __dict__ so have to use setattr
        for attr, value in values.items():
            setattr(self, attr, value)

    def node_repr(node):
        """A generic __repr__ method for the nodes."""
        s = "(" + node.__class__.__name__ + " "
        slot_reprs = []
        for slot in node.__slots__:
            if slot == "line": continue
            attr = getattr(node, slot, None)
            if attr is None:
                continue
            elif isinstance(attr, list):
                reprlist = map(repr, attr)
                slot_reprs.append("(list " + " ".join(reprlist) + ")")
            else:
                slot_reprs.append(repr(attr))
        s += " ".join(slot_reprs) + ")"
        return s

    # construct a new type and return it
    # "line" will be appended to __slots__ automatically
    return type(node_type, (BaseNode,), {
        "__init__": node_init,
        "__slots__": slots.split() + ["line"],
        "__repr__": node_repr})


# ast node types
# for expressions
StructAccess = node("StructAccess", "left right")
SLiteral = node("SLiteral", "value")
Variable = node("Variable", "name")
ILiteral = node("ILiteral", "value")
UnaryOp = node("UnaryOp", "op right")
PointerOp = node("PointerOp", "op right level")
BinaryOp = node("BinaryOp", "op left right")
Condition = node("Condition", "op left right")

# statements
# control flow for loops
CtrlStatement = node("CtrlStatement", "op")
RetStatement = node("RetStatement", "value")
StoreStatement = node("StoreStatement", "level ptr value")
VarDeclStatement = node("VarDeclStatement", "type name")
StructStoreStatement = node("StructStoreStatement", "struct value")
AssignStatement = node("AssignStatement", "var value")
WhileStatement = node("WhileStatement", "cond stmt")
IfStatement = node("IfStatement", "cond stmt elsestmt")
BlockStatement = node("BlockStatement", "stmts")
FCallStatement = node("FCallStatement", "name args")
Func = node("Func", "type name args stmt")
Struct = node("Struct", "name decls")

# misc
Type = node("Type", "type level")



