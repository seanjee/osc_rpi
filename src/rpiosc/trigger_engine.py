from __future__ import annotations

import time
from dataclasses import dataclass

from rpiosc.gpio_driver import EdgeEvent, EdgeKind
from rpiosc.models import TriggerMode
from rpiosc.trigger_dsl import (
    And,
    ChannelEdge,
    ChannelLevel,
    Edge,
    Expr,
    Level,
    Not,
    Or,
    WithinAfter,
    WithinBefore,
)


@dataclass(frozen=True)
class TriggerDecision:
    triggered: bool
    reason: str
    timestamp_ns: int


class TriggerEngine:
    def __init__(
        self,
        *,
        expr: Expr,
        mode: TriggerMode,
        holdoff_s: float,
        auto_timeout_s: float = 0.5,
    ):
        self._expr = expr
        self._mode = mode
        self._holdoff_s = holdoff_s
        self._auto_timeout_s = auto_timeout_s

        self._last_trigger_ns: int | None = None
        self._single_done = False
        self._last_auto_fire_monotonic = time.monotonic()

        self._last_level_by_ch: dict[int, int] = {}
        self._last_edge_ns_by_ch: dict[int, dict[EdgeKind, int]] = {}
        self._edges_seen_this_batch: dict[int, set[EdgeKind]] = {}

    @property
    def mode(self) -> TriggerMode:
        return self._mode

    @property
    def holdoff_s(self) -> float:
        return self._holdoff_s

    def set_holdoff(self, holdoff_s: float) -> None:
        self._holdoff_s = max(0.0, float(holdoff_s))

    def set_mode(self, mode: TriggerMode) -> None:
        self._mode = mode
        if mode != TriggerMode.SINGLE:
            self._single_done = False

    def set_expr(self, expr: Expr) -> None:
        self._expr = expr

    def reset_single(self) -> None:
        self._single_done = False

    def process(self, events: list[EdgeEvent]) -> TriggerDecision | None:
        now_ns = time.time_ns()

        if self._mode == TriggerMode.SINGLE and self._single_done:
            return None

        if self._last_trigger_ns is not None:
            if (now_ns - self._last_trigger_ns) < int(self._holdoff_s * 1e9):
                self._ingest(events)
                return None

        # Track edges seen in this batch for BOTH edge detection
        self._edges_seen_this_batch = {}
        for ev in events:
            self._edges_seen_this_batch.setdefault(ev.channel_id, set()).add(ev.edge)

        self._ingest(events)

        if self._evaluate(self._expr, new_edges=self._edges_seen_this_batch):
            return self._fire("TRIGGER")

        return None

    def _fire(self, reason: str) -> TriggerDecision:
        # Use the edge event timestamp from _get_trigger_timestamp
        trigger_ts = self._get_trigger_timestamp()
        if trigger_ts is None:
            trigger_ts = time.time_ns()

        self._last_trigger_ns = trigger_ts
        if reason == "TRIGGER":
            self._consume_edges_for_trigger(self._expr)
        if self._mode == TriggerMode.SINGLE and reason == "TRIGGER":
            self._single_done = True
        return TriggerDecision(triggered=True, reason=reason, timestamp_ns=trigger_ts)

    def _get_trigger_timestamp(self) -> int | None:
        """Get the timestamp of the edge event that caused the trigger."""
        # Check which edge(s) in the current batch caused the trigger
        if isinstance(self._expr, ChannelEdge):
            if self._expr.edge == Edge.BOTH:
                # For BOTH edges, use the most recent edge timestamp from the batch
                ch_edges = self._last_edge_ns_by_ch.get(self._expr.channel, {})
                if not ch_edges:
                    return None
                # Return the most recent edge timestamp
                return max(ch_edges.values())
            else:
                # For single edge type, return that edge's timestamp
                kind = _edge_to_kind(self._expr.edge)
                return self._last_edge_ns_by_ch.get(self._expr.channel, {}).get(kind)
        return None

    def _consume_edges_for_trigger(self, expr: Expr) -> None:
        if isinstance(expr, ChannelEdge):
            kind = _edge_to_kind(expr.edge)
            try:
                del self._last_edge_ns_by_ch.get(expr.channel, {})[kind]
            except Exception:
                pass
            return

        if isinstance(expr, And):
            self._consume_edges_for_trigger(expr.left)
            self._consume_edges_for_trigger(expr.right)
            return

        if isinstance(expr, Or):
            self._consume_edges_for_trigger(expr.left)
            self._consume_edges_for_trigger(expr.right)
            return

        if isinstance(expr, Not):
            self._consume_edges_for_trigger(expr.expr)
            return

        if isinstance(expr, WithinAfter):
            self._consume_edges_for_trigger(expr.expr)
            self._consume_edges_for_trigger(expr.anchor)
            return

        if isinstance(expr, WithinBefore):
            self._consume_edges_for_trigger(expr.expr)
            self._consume_edges_for_trigger(expr.anchor)
            return

    def _ingest(self, events: list[EdgeEvent]) -> None:
        for ev in events:
            self._last_edge_ns_by_ch.setdefault(ev.channel_id, {})[ev.edge] = ev.timestamp_ns
            if ev.edge == EdgeKind.RISING:
                self._last_level_by_ch[ev.channel_id] = 1
            elif ev.edge == EdgeKind.FALLING:
                self._last_level_by_ch[ev.channel_id] = 0

    def _evaluate(self, expr: Expr, new_edges: dict[int, set[EdgeKind]] | None = None) -> bool:
        if isinstance(expr, ChannelEdge):
            # true if edge was just seen in this batch
            if new_edges is None:
                # Fallback for backward compatibility
                if expr.edge == Edge.BOTH:
                    ch_edges = self._last_edge_ns_by_ch.get(expr.channel, {})
                    return EdgeKind.RISING in ch_edges or EdgeKind.FALLING in ch_edges
                kind = _edge_to_kind(expr.edge)
                return kind in self._last_edge_ns_by_ch.get(expr.channel, {})
            else:
                # Check if this specific edge was just seen
                edges_this_batch = new_edges.get(expr.channel, set())
                if expr.edge == Edge.BOTH:
                    return EdgeKind.RISING in edges_this_batch or EdgeKind.FALLING in edges_this_batch
                kind = _edge_to_kind(expr.edge)
                return kind in edges_this_batch

        if isinstance(expr, ChannelLevel):
            want = 1 if expr.level == Level.HIGH else 0
            return self._last_level_by_ch.get(expr.channel) == want

        if isinstance(expr, Not):
            return not self._evaluate(expr.expr, new_edges)

        if isinstance(expr, And):
            return self._evaluate(expr.left, new_edges) and self._evaluate(expr.right, new_edges)

        if isinstance(expr, Or):
            return self._evaluate(expr.left, new_edges) or self._evaluate(expr.right, new_edges)

        if isinstance(expr, WithinAfter):
            # window predicate is considered true only at the moment `expr` edge occurs
            if isinstance(expr.expr, ChannelEdge):
                edges_this_batch = new_edges.get(expr.expr.channel, set()) if new_edges else set()
                if expr.expr.edge == Edge.BOTH:
                    # For BOTH, check if either edge was just seen
                    if not (EdgeKind.RISING in edges_this_batch or EdgeKind.FALLING in edges_this_batch):
                        return False
                else:
                    kind = _edge_to_kind(expr.expr.edge)
                    if kind not in edges_this_batch:
                        return False
            return _within(
                self._last_edge_ns_by_ch,
                expr.expr,
                expr.anchor,
                expr.window_seconds,
                after=True,
            )

        if isinstance(expr, WithinBefore):
            return _within(
                self._last_edge_ns_by_ch,
                expr.expr,
                expr.anchor,
                expr.window_seconds,
                after=False,
            )

        raise TypeError(f"Unsupported expr: {type(expr)}")


def _edge_to_kind(edge: Edge) -> EdgeKind:
    if edge == Edge.RISING:
        return EdgeKind.RISING
    if edge == Edge.FALLING:
        return EdgeKind.FALLING
    # BOTH treated as either edge seen; evaluation checks presence of either
    return EdgeKind.RISING


def _expr_last_edge_ns(
    last_edges: dict[int, dict[EdgeKind, int]],
    expr: Expr,
) -> int | None:
    if isinstance(expr, ChannelEdge):
        if expr.edge == Edge.BOTH:
            d = last_edges.get(expr.channel, {})
            return max(d.values()) if d else None
        kind = EdgeKind.RISING if expr.edge == Edge.RISING else EdgeKind.FALLING
        return last_edges.get(expr.channel, {}).get(kind)

    if isinstance(expr, WithinAfter):
        # For nested timing expressions, use the timestamp of the inner expr.
        return _expr_last_edge_ns(last_edges, expr.expr)

    if isinstance(expr, WithinBefore):
        return _expr_last_edge_ns(last_edges, expr.expr)

    return None


def _within(
    last_edges: dict[int, dict[EdgeKind, int]],
    expr: Expr,
    anchor: Expr,
    window_s: float,
    *,
    after: bool,
) -> bool:
    expr_ts = _expr_last_edge_ns(last_edges, expr)
    anchor_ts = _expr_last_edge_ns(last_edges, anchor)
    if expr_ts is None or anchor_ts is None:
        return False
    window_ns = int(window_s * 1e9)
    if after:
        return 0 <= (expr_ts - anchor_ts) <= window_ns
    return 0 <= (anchor_ts - expr_ts) <= window_ns
