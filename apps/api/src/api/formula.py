"""Safe formula evaluator for analysis pack proxy formulas.

This module implements a restricted arithmetic parser that evaluates
formula strings like "Rb / Sr" against a symbol table of column values.
It explicitly does NOT use Python's eval() or exec() — formulas are
parsed into an AST and evaluated node by node with strict bounds.

Security boundary: formulas may contain only:
  - Variable names matching [a-zA-Z_][a-zA-Z0-9_]*
  - Numeric literals (integers and floats)
  - Operators: +, -, *, /
  - Parentheses for grouping

Anything else raises FormulaError.
"""

import re
from dataclasses import dataclass


class FormulaError(Exception):
    """Raised when a formula string is invalid or cannot be evaluated."""


class DivisionByZeroError(FormulaError):
    """Raised when a formula divides by zero."""


class MissingVariableError(FormulaError):
    """Raised when a formula references a variable not in the symbol table."""


# --- Tokeniser ---

TOKEN_RE = re.compile(r"""
    \s*(?:
        (?P<NUMBER>  \d+\.?\d*  )
        |(?P<VAR>    [a-zA-Z_][a-zA-Z0-9_]*  )
        |(?P<PLUS>   \+ )
        |(?P<MINUS>  -  )
        |(?P<TIMES>  \* )
        |(?P<DIVIDE> /  )
        |(?P<LPAREN> \( )
        |(?P<RPAREN> \) )
        |(?P<ERROR>  .  )
    )
""", re.VERBOSE)


@dataclass
class Token:
    kind: str
    value: str
    pos: int


def tokenise(expression: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(expression):
        m = TOKEN_RE.match(expression, pos)
        if m is None:
            raise FormulaError(f"Unexpected character at position {pos}: {expression[pos]!r}")
        kind = m.lastgroup
        assert kind is not None
        text = m.group(kind)
        if kind == "ERROR":
            raise FormulaError(f"Unexpected character {text!r} at position {pos}")
        tokens.append(Token(kind, text, pos))
        pos = m.end()
    tokens.append(Token("EOF", "", pos))
    return tokens


# --- AST Nodes ---

@dataclass
class Num:
    value: float


@dataclass
class Var:
    name: str


@dataclass
class BinOp:
    op: str
    left: object
    right: object


@dataclass
class UnaryMinus:
    operand: object


# --- Parser (recursive descent) ---


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind: str) -> Token:
        tok = self.peek()
        if tok.kind != kind:
            raise FormulaError(
            f"Expected {kind}, got {tok.kind!r} ({tok.value!r}) at position {tok.pos}"
        )
        return self.advance()

    def parse(self) -> object:
        ast = self.parse_expr()
        if self.peek().kind != "EOF":
            raise FormulaError(f"Unexpected token {self.peek().value!r} after expression")
        return ast

    # expr ::= term ( ("+" | "-") term )*
    def parse_expr(self) -> object:
        left = self.parse_term()
        while self.peek().kind in ("PLUS", "MINUS"):
            op = self.advance().kind
            right = self.parse_term()
            left = BinOp("+" if op == "PLUS" else "-", left, right)
        return left

    # term ::= unary ( ("*" | "/") unary )*
    def parse_term(self) -> object:
        left = self.parse_unary()
        while self.peek().kind in ("TIMES", "DIVIDE"):
            op = self.advance().kind
            right = self.parse_unary()
            left = BinOp("*" if op == "TIMES" else "/", left, right)
        return left

    # unary ::= "-" unary | primary
    def parse_unary(self) -> object:
        if self.peek().kind == "MINUS":
            self.advance()
            operand = self.parse_unary()
            return UnaryMinus(operand)
        return self.parse_primary()

    # primary ::= NUMBER | VAR | "(" expr ")"
    def parse_primary(self) -> object:
        tok = self.peek()
        if tok.kind == "NUMBER":
            self.advance()
            if "." in tok.value:
                return Num(float(tok.value))
            return Num(int(tok.value))
        if tok.kind == "VAR":
            self.advance()
            return Var(tok.value)
        if tok.kind == "LPAREN":
            self.advance()
            ast = self.parse_expr()
            self.expect("RPAREN")
            return ast
        raise FormulaError(f"Unexpected token {tok.value!r} at position {tok.pos}")


# --- Evaluator ---


def evaluate(ast: object, variables: dict[str, float]) -> float:
    """Evaluate an AST against a symbol table.

    Raises:
        MissingVariableError: if a variable is not in the symbol table.
        DivisionByZeroError: if a division by zero is attempted.
        FormulaError: for any other evaluation error.
    """
    match ast:
        case Num(value=v):
            return float(v)
        case Var(name=n):
            if n not in variables:
                raise MissingVariableError(f"Variable {n!r} is not defined")
            return variables[n]
        case UnaryMinus(operand=o):
            return -evaluate(o, variables)
        case BinOp(op=op, left=l, right=r):
            left_val = evaluate(l, variables)
            right_val = evaluate(r, variables)
            if op == "+":
                return left_val + right_val
            elif op == "-":
                return left_val - right_val
            elif op == "*":
                return left_val * right_val
            elif op == "/":
                if right_val == 0.0:
                    raise DivisionByZeroError("Division by zero in formula")
                return left_val / right_val
            else:
                raise FormulaError(f"Unknown operator {op!r}")
        case _:
            raise FormulaError(f"Unknown AST node {ast!r}")


def eval_formula(formula: str, variables: dict[str, float]) -> float:
    """Parse and evaluate a formula string safely.

    This is the single public entry point. It combines tokenising,
    parsing, and evaluation into one call.

    Example:
        >>> eval_formula("Rb / Sr", {"Rb": 200.0, "Sr": 59.0})
        3.389830508474576
    """
    tokens = tokenise(formula)
    parser = Parser(tokens)
    ast = parser.parse()
    return evaluate(ast, variables)
