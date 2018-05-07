# main.py
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

import sys

from lexer import Lexer
import parser
import typecheck


userdefined = {
    # "atoms" which don't have any special value
    "atom": ["while", "if", "else", "return", "struct", "sizeof"]
        + [">>>", ">>", "<<", "<", ">" "<=", ">=", "!=", "=="]
        + list("(){}*/+-~|&^=<>,.;"),
}


def main(argv):
    if len(argv) != 2:
        print("usage:", argv[0], "sourcefile")
        return 2
    
    source = ""
    try:
        with open(argv[1], "r") as f:
            source = f.read()
    except IOError as e:
        print("failed to open source file:", e)
        return 1

    try:
        # create a lexer object
        # note: the same object can be used to tokenize multiple source files
        # (possibly thread-safe)
        lexer = Lexer(userdefined)
        tokens = lexer.tokenize(source)

        funcs, structs = parser.parse(tokens)

        # for debug purposes; this will be removed or changed later
        print("[debug] ast")
        print("(structs", " ".join(map(repr, structs)), ")")
        print()
        print("(funcs", " ".join(map(repr, funcs)), ")")

        # perform type and scope checking
        struct_dict = typecheck.check_structs(structs)
        print(struct_dict, "\n")
        aast = typecheck.check_funcs(funcs, struct_dict)
        print("(aast", " ".join(map(repr, aast)), ")")

        
    # add LexerException later if needed
    except (parser.ParserException, typecheck.SemanticsException) as e:
        print(argv[1] + ":", e)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

