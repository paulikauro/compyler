# lexer.py: a simple lexer implemented using regular expressions
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

import re

class LexerException(Exception):
    def __init__(self, msg, line):
        super().__init__("lexer: {}: {}".format(str(line), msg))


class Token(object):
    def __init__(self, token_type, value, line):
        self.type = token_type
        self.value = value
        self.line = line
        # line information is used by later passes in the compiler
        # to generate meaningful error messages

    def __eq__(self, other):
        # this is just to make parsing easier
        # token.type == "type" vs token == "type"
        if isinstance(other, Token):
            return self.type == other.type
        else:
            return self.type == other
    
    def __repr__(self):
        return "line {}: {}\t '{}'".format(self.line, self.type, self.value)


class Lexer(object):
    # a semi-generic regex for matching a token
    # this will handle:
    # - whitespace characters and comments
    # - quoted strings ("") with escapes
    # - hex and decimal integer literals
    # - identifiers
    regex = r"""
        # skip over whitespace and comments with non-capturing groups
        (?: \s*)
        (?: [#] [^\n]* \n \s*)*

        # actual tokens
        (
        # strings
        (?P<str>\"(\\.|[^\\\"])*\") (?=\W) |

        # hex integer literals
        (?P<hex>0x[0-9a-fA-F]+) (?=\W) |

        # decimal integer literals
        (?P<int>\d+) (?=\W) |

        # for user-defined tokens
        {}

        # identifiers
        (?P<id>[a-zA-Z_]\w*)
        )
    """

    def __init__(self, userdefined):
        s = ""
        # go over the dict of user defined tokens
        for k, v in userdefined.items():
            # key: token group, value: list of what to match
            # escape the values
            escaped = [re.escape(val) for val in v]
            # join into a named regex pattern
            s += "(?P<{}>{}) |".format(k, "|".join(escaped))

        # format into the generic regex
        r = Lexer.regex.format(s)

        # compile the pattern to avoid overhead
        # since it will be used so many times
        self.pattern = re.compile(r, re.VERBOSE | re.MULTILINE)

    def tokenize(self, src):
        pos = 0
        line = 1
        while True:
            m = self.pattern.match(src, pos)
            # no match
            if not m: break
            # keep track of position
            pos = m.end()
            # count newlines in the matched portion of the source
            line += src[m.start():m.end()].count("\n")

            for k, v in m.groupdict().items():
                if v is not None:
                    # fix some names
                    if k == "hex":
                        v = int(v, 16)
                        k = "int"
                    elif k == "int":
                        v = int(v)
                    elif k == "atom":
                        # this makes parsing easier
                        k = v

                    yield Token(k, v, line)

                    # since there should be only one group that matches
                    # we can safely break out of iterating the groupdict
                    break

