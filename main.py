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
#import parser


userdefined = {
    # "atoms" which don't have any special value
    "atom": ["while", "if", "else", "return"]
        + ["+=", "-=", "<=", ">=", "=="]
        + list("(){}[]@+-~|&^=<>,"),

    # types are nice to have separately though
    "type": ["u0", "u8", "u16"]
}


def main(argv):
    if len(argv) != 2:
        print("usage:", argv[0], "sourcefile")
        return 2
    
    source = ""
    try:
        with open("test", "r") as f:
            source = f.read()
    except IOError as e:
        print("failed to open source file:", e)
        return 1

    print("source dump\n", source, "\n")
    lexer = Lexer(userdefined)
    tokens = lexer.tokenize(source)
    for tok in tokens:
        print(tok)
    
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

