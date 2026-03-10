from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Edge(str, Enum):
    RISING = "Rising"
    FALLING = "Falling"
    BOTH = "Both"


class Level(str, Enum):
    HIGH = "High"
    LOW = "Low"


@dataclass(frozen=True)
class Expr:
    pass


@dataclass(frozen=True)
class ChannelEdge(Expr):
    channel: int
    edge: Edge


@dataclass(frozen=True)
class ChannelLevel(Expr):
    channel: int
    level: Level


@dataclass(frozen=True)
class Not(Expr):
    expr: Expr


@dataclass(frozen=True)
class And(Expr):
    left: Expr
    right: Expr


@dataclass(frozen=True)
class Or(Expr):
    left: Expr
    right: Expr


@dataclass(frozen=True)
class WithinAfter(Expr):
    expr: Expr
    window_seconds: float
    anchor: Expr


@dataclass(frozen=True)
class WithinBefore(Expr):
    expr: Expr
    window_seconds: float
    anchor: Expr


class ParseError(ValueError):
    def __init__(self, message: str, position: int):
        super().__init__(message)
        self.position = position


def parse_expression(text: str) -> Expr:
    parser = _Parser(text)
    expr = parser.parse_or()
    parser.skip_ws()
    if not parser.eof():
        raise ParseError(f"Unexpected token '{parser.peek()}'", parser.pos)
    return expr


class _Parser:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0

    def eof(self) -> bool:
        return self.pos >= len(self.text)

    def peek(self) -> str:
        return self.text[self.pos : self.pos + 1]

    def skip_ws(self) -> None:
        while not self.eof() and self.text[self.pos].isspace():
            self.pos += 1

    def consume(self, s: str) -> bool:
        self.skip_ws()
        if self.text.startswith(s, self.pos):
            self.pos += len(s)
            return True
        return False

    def expect(self, s: str) -> None:
        if not self.consume(s):
            raise ParseError(f"Expected '{s}'", self.pos)

    def parse_or(self) -> Expr:
        left = self.parse_and()
        while True:
            if self.consume("OR"):
                right = self.parse_and()
                left = Or(left, right)
            else:
                break
        return left

    def parse_and(self) -> Expr:
        left = self.parse_unary()
        while True:
            if self.consume("AND"):
                right = self.parse_unary()
                left = And(left, right)
            else:
                break
        return left

    def parse_unary(self) -> Expr:
        self.skip_ws()
        if self.consume("NOT"):
            return Not(self.parse_unary())
        return self.parse_primary()

    def parse_primary(self) -> Expr:
        self.skip_ws()
        if self.consume("(") or self.consume("["):
            expr = self.parse_or()
            self.skip_ws()
            if self.consume(")") or self.consume("]"):
                pass
            else:
                raise ParseError("Expected closing bracket", self.pos)
            return expr

        # Channel conditions
        if self.text.startswith("CH", self.pos):
            return self.parse_channel_condition()

        raise ParseError("Expected expression", self.pos)

    def parse_channel_condition(self) -> Expr:
        self.skip_ws()
        start = self.pos
        self.expect("CH")
        ch_num = self.parse_int()
        self.skip_ws()

        # Level condition: CHn = High
        if self.consume("="):
            self.skip_ws()
            if self.consume("High"):
                return ChannelLevel(ch_num, Level.HIGH)
            if self.consume("Low"):
                return ChannelLevel(ch_num, Level.LOW)
            raise ParseError("Expected level 'High' or 'Low'", self.pos)

        # Edge condition: CHn Rising/Falling[/Both Edges]
        # Also accept shorthand "CHn" meaning "CHn Rising" (observed in trigger_conditions.yaml example: "after CH1")
        if self.consume("Rising"):
            base: Expr = ChannelEdge(ch_num, Edge.RISING)
        elif self.consume("Falling"):
            base = ChannelEdge(ch_num, Edge.FALLING)
        elif self.consume("Both"):
            self.skip_ws()
            # Accept both forms:
            # - "CH1 Both" (shorthand)
            # - "CH1 Both Edges" (explicit)
            _ = self.consume("Edges")
            base = ChannelEdge(ch_num, Edge.BOTH)
        else:
            base = ChannelEdge(ch_num, Edge.RISING)

        # Optional timing clause: within 10ms after CH1 Rising
        self.skip_ws()
        if self.consume("within"):
            self.skip_ws()
            window = self.parse_duration_seconds()
            self.skip_ws()
            if self.consume("after"):
                anchor = self.parse_primary()
                return WithinAfter(base, window, anchor)
            if self.consume("before"):
                anchor = self.parse_primary()
                return WithinBefore(base, window, anchor)
            raise ParseError("Expected 'after' or 'before'", self.pos)

        _ = start
        return base

    def parse_int(self) -> int:
        self.skip_ws()
        start = self.pos
        while not self.eof() and self.text[self.pos].isdigit():
            self.pos += 1
        if self.pos == start:
            raise ParseError("Expected integer", self.pos)
        return int(self.text[start:self.pos])

    def parse_duration_seconds(self) -> float:
        self.skip_ws()
        start = self.pos
        while not self.eof() and (self.text[self.pos].isdigit() or self.text[self.pos] == "."):
            self.pos += 1
        if self.pos == start:
            raise ParseError("Expected duration number", self.pos)
        value = float(self.text[start:self.pos])
        self.skip_ws()

        # Units observed in PRD/examples: ms, μs (also allow us as ASCII)
        if self.consume("ms"):
            return value / 1000.0
        if self.consume("μs") or self.consume("us"):
            return value / 1_000_000.0
        if self.consume("s"):
            return value

        raise ParseError("Expected duration unit (μs/us/ms/s)", self.pos)
