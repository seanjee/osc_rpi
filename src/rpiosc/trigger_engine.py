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
    channel_id: int | None = None
    edge: EdgeKind | None = None
    detail: str = ""


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
        # libgpiod timestamps are monotonic; use event time when available so
        # holdoff logic is consistent even if wall-clock time jumps.
        if events:
            now_ns = max(int(ev.timestamp_ns) for ev in events)
        else:
            now_ns = time.monotonic_ns()

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
            return self._fire("TRIGGER", now_ns=now_ns)

        return None

    def _fire(self, reason: str, *, now_ns: int) -> TriggerDecision:
        # Always keep timestamps in the monotonic timebase (libgpiod event timestamps / time.monotonic_ns)
        # so holdoff and window comparisons remain valid.
        trigger_ts = self._get_trigger_timestamp(self._expr)
        if trigger_ts is None:
            trigger_ts = int(now_ns)

        ch, edge = self._get_trigger_source(trigger_ts)
        detail = ""
        if ch is not None and edge is not None:
            detail = f"CH{ch} {edge.value}"

        self._last_trigger_ns = trigger_ts
        if reason == "TRIGGER":
            self._consume_edges_for_trigger(self._expr)
        if self._mode == TriggerMode.SINGLE and reason == "TRIGGER":
            self._single_done = True
        return TriggerDecision(
            triggered=True,
            reason=reason,
            timestamp_ns=trigger_ts,
            channel_id=ch,
            edge=edge,
            detail=detail,
        )

    def _get_trigger_source(self, trigger_ts: int) -> tuple[int | None, EdgeKind | None]:
        """Best-effort extraction of the channel/edge that corresponds to trigger_ts."""
        # Only reliable for simple ChannelEdge expressions.
        if isinstance(self._expr, ChannelEdge):
            ch = int(self._expr.channel)
            d = self._last_edge_ns_by_ch.get(ch, {})
            if not d:
                return ch, None
            if self._expr.edge == Edge.BOTH:
                # Choose the edge kind whose timestamp matches the selected trigger timestamp.
                for kind, ts in d.items():
                    if int(ts) == int(trigger_ts):
                        return ch, kind
                # Fallback: pick the most recent.
                kind = max(d.items(), key=lambda kv: int(kv[1]))[0]
                return ch, kind
            kind = _edge_to_kind(self._expr.edge)
            return ch, kind
        return None, None

    def _get_trigger_timestamp(self, expr: Expr) -> int | None:
        """Best-effort timestamp for the expression that caused the trigger.

        For timing/window expressions:
        - WithinAfter: align to the inner edge (expr), i.e. the edge that occurs within the window.
        - WithinBefore: align to the anchor edge, i.e. the edge whose arrival makes the condition knowable.
        """
        if isinstance(expr, WithinBefore):
            return _expr_last_edge_ns(self._last_edge_ns_by_ch, expr.anchor)
        return _expr_last_edge_ns(self._last_edge_ns_by_ch, expr)

    def _consume_edges_for_trigger(self, expr: Expr) -> None:
        if isinstance(expr, ChannelEdge):
            try:
                ch_edges = self._last_edge_ns_by_ch.get(expr.channel, {})
                if expr.edge == Edge.BOTH:
                    ch_edges.pop(EdgeKind.RISING, None)
                    ch_edges.pop(EdgeKind.FALLING, None)
                else:
                    kind = _edge_to_kind(expr.edge)
                    ch_edges.pop(kind, None)
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
            # "within ... before ANCHOR" should only be considered at the moment the anchor edge arrives.
            if isinstance(expr.anchor, ChannelEdge):
                edges_this_batch = new_edges.get(expr.anchor.channel, set()) if new_edges else set()
                if expr.anchor.edge == Edge.BOTH:
                    if not (EdgeKind.RISING in edges_this_batch or EdgeKind.FALLING in edges_this_batch):
                        return False
                else:
                    kind = _edge_to_kind(expr.anchor.edge)
                    if kind not in edges_this_batch:
                        return False
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
