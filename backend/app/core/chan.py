"""
缠论 algorithm: merge K-bars, detect fractals, detect pens.

Pipeline:
    raw bars  --merge_kbars-->  merged bars
    merged bars  --detect_fractals-->  fractals (top/bottom)
    fractals  --detect_pens-->  pens (up/down line segments)

Each pen endpoint is mapped back to an original raw-bar index so the
frontend can plot the pen on the original candlestick chart.
"""
from dataclasses import dataclass, field
from typing import List, Literal


@dataclass
class Bar:
    """Original (raw) K-line bar."""
    idx: int
    date: str
    high: float
    low: float


@dataclass
class MergedBar:
    """A merged K-line after containment processing."""
    idx_start: int          # raw idx of the first contributing bar
    idx_end: int            # raw idx of the last contributing bar
    high: float
    low: float
    src_indices: List[int] = field(default_factory=list)


@dataclass
class Fractal:
    """A top or bottom fractal located on the merged-bar sequence."""
    type: Literal['top', 'bottom']
    merged_idx: int         # index into the merged bars list
    price: float            # high for top, low for bottom


@dataclass
class Pen:
    """A 笔 connecting a bottom fractal to a top fractal (or vice versa)."""
    direction: Literal['up', 'down']
    start_merged_idx: int
    end_merged_idx: int
    start_src_idx: int      # raw-bar idx at the pen's start endpoint
    end_src_idx: int        # raw-bar idx at the pen's end endpoint
    start_price: float
    end_price: float


# ---------------------------------------------------------------------------
# Stage 1: merge raw bars into containment-free merged bars
# ---------------------------------------------------------------------------

def _is_contained(a_high: float, a_low: float, b_high: float, b_low: float) -> bool:
    """True if A contains B or B contains A."""
    return (a_high >= b_high and a_low <= b_low) or (b_high >= a_high and b_low <= a_low)


def _detect_initial_direction(bars: List[Bar]) -> Literal['up', 'down']:
    """
    Scan forward for the first pair of non-containing bars to determine
    the initial trend direction.  Falls back to 'up' if all bars contain
    each other (extreme edge case).
    """
    for i in range(len(bars) - 1):
        a, b = bars[i], bars[i + 1]
        if _is_contained(a.high, a.low, b.high, b.low):
            continue
        return 'up' if b.high > a.high else 'down'
    return 'up'


def merge_kbars(bars: List[Bar]) -> List[MergedBar]:
    """Fold containment relationships into merged bars.

    MergedBar instances inside the returned list are mutated in place during
    accumulation (their high/low/idx_end/src_indices grow as more raw bars
    fold into them), which is normal — callers should treat the returned
    list as the final result and not reuse intermediate references.
    """
    if not bars:
        return []

    direction: Literal['up', 'down'] = _detect_initial_direction(bars)
    merged: List[MergedBar] = [MergedBar(
        idx_start=bars[0].idx, idx_end=bars[0].idx,
        high=bars[0].high, low=bars[0].low,
        src_indices=[bars[0].idx],
    )]

    for bar in bars[1:]:
        top = merged[-1]
        if _is_contained(top.high, top.low, bar.high, bar.low):
            # Containment relationship: merge using current direction.
            if direction == 'up':
                new_high = max(top.high, bar.high)
                new_low = max(top.low, bar.low)
            else:
                new_high = min(top.high, bar.high)
                new_low = min(top.low, bar.low)
            top.high = new_high
            top.low = new_low
            top.idx_end = bar.idx
            top.src_indices.append(bar.idx)
        else:
            # Non-containment: update direction based on the new bar vs the merged top.
            direction = 'up' if bar.high > top.high else 'down'
            merged.append(MergedBar(
                idx_start=bar.idx, idx_end=bar.idx,
                high=bar.high, low=bar.low,
                src_indices=[bar.idx],
            ))

    return merged


# ---------------------------------------------------------------------------
# Stage 2: detect top / bottom fractals
# ---------------------------------------------------------------------------

def detect_fractals(merged: List[MergedBar]) -> List[Fractal]:
    """Sliding window of 3 merged bars; strict greater/less for top/bottom."""
    fractals: List[Fractal] = []
    for i in range(1, len(merged) - 1):
        prev, mid, nxt = merged[i - 1], merged[i], merged[i + 1]
        if mid.high > prev.high and mid.high > nxt.high \
                and mid.low > prev.low and mid.low > nxt.low:
            fractals.append(Fractal(type='top', merged_idx=i, price=mid.high))
        elif mid.high < prev.high and mid.high < nxt.high \
                and mid.low < prev.low and mid.low < nxt.low:
            fractals.append(Fractal(type='bottom', merged_idx=i, price=mid.low))
    return fractals


# ---------------------------------------------------------------------------
# Stage 3: build pens from fractals
# ---------------------------------------------------------------------------

MIN_FRACTAL_GAP = 4
"""
Minimum gap (in merged-bar indices) between two opposing fractals.

A bottom fractal occupies merged idx (i-1, i, i+1) and a top fractal
occupies (j-1, j, j+1).  For them to share no bars AND have ≥1 fully
independent merged K between them, we need j - i ≥ 4
(bottom_middle=i, right_of_bottom=i+1, independent=i+2, left_of_top=i+3, top_middle=i+4=j).
"""


def _src_idx_for_high(merged: MergedBar, raw_bars: List[Bar] | None) -> int:
    """Return the raw-bar index inside merged with the highest 'high'.

    raw_bars may be None when each merged bar has exactly one source
    (e.g. in unit tests with hand-crafted merged sequences).
    """
    if raw_bars is None or len(merged.src_indices) == 1:
        return merged.src_indices[0] if merged.src_indices else merged.idx_start
    best_idx = merged.src_indices[0]
    best_val = raw_bars[best_idx].high
    for si in merged.src_indices[1:]:
        if raw_bars[si].high > best_val:
            best_val = raw_bars[si].high
            best_idx = si
    return best_idx


def _src_idx_for_low(merged: MergedBar, raw_bars: List[Bar] | None) -> int:
    """Return the raw-bar index inside merged with the lowest 'low'.

    raw_bars may be None when each merged bar has exactly one source.
    """
    if raw_bars is None or len(merged.src_indices) == 1:
        return merged.src_indices[0] if merged.src_indices else merged.idx_start
    best_idx = merged.src_indices[0]
    best_val = raw_bars[best_idx].low
    for si in merged.src_indices[1:]:
        if raw_bars[si].low < best_val:
            best_val = raw_bars[si].low
            best_idx = si
    return best_idx


def detect_pens(
    merged: List[MergedBar],
    fractals: List[Fractal],
    raw_bars: List[Bar] | None = None,
) -> List[Pen]:
    """
    Build pens (笔) from the fractal list.

    Rules:
      - tops and bottoms must alternate; consecutive same-type fractals are
        replaced by the more extreme one (lower bottom / higher top)
      - opposing fractals must be ≥ MIN_FRACTAL_GAP merged-bars apart;
        otherwise the new fractal is discarded
      - adjacent pens share an endpoint: pen[i].end is the same fractal as
        pen[i+1].start.  If after a pen forms a more-extreme same-type fractal
        appears, the previous pen's endpoint is extended to it so the chain
        stays connected.
    """
    if not fractals:
        return []

    pens: List[Pen] = []
    pending = fractals[0]

    for f in fractals[1:]:
        if f.type == pending.type:
            # same type → keep the more extreme one
            is_more_extreme = (f.type == 'top' and f.price > pending.price) or \
                              (f.type == 'bottom' and f.price < pending.price)
            if is_more_extreme:
                pending = f
                # If we already formed a pen ending at the old pending, extend
                # that pen so adjacent pens stay connected.
                if pens and pens[-1].end_merged_idx != f.merged_idx:
                    last = pens[-1]
                    end_merged = merged[f.merged_idx]
                    if last.direction == 'up':
                        end_src = _src_idx_for_high(end_merged, raw_bars)
                    else:
                        end_src = _src_idx_for_low(end_merged, raw_bars)
                    last.end_merged_idx = f.merged_idx
                    last.end_src_idx = end_src
                    last.end_price = f.price
            continue

        # opposite type
        gap = f.merged_idx - pending.merged_idx
        if gap < MIN_FRACTAL_GAP:
            # gap too small → discard the new fractal and wait
            continue

        # form a pen
        direction: Literal['up', 'down'] = 'up' if pending.type == 'bottom' else 'down'
        start_merged = merged[pending.merged_idx]
        end_merged = merged[f.merged_idx]
        if direction == 'up':
            start_src_idx = _src_idx_for_low(start_merged, raw_bars)
            end_src_idx = _src_idx_for_high(end_merged, raw_bars)
        else:
            start_src_idx = _src_idx_for_high(start_merged, raw_bars)
            end_src_idx = _src_idx_for_low(end_merged, raw_bars)
        pens.append(Pen(
            direction=direction,
            start_merged_idx=pending.merged_idx,
            end_merged_idx=f.merged_idx,
            start_src_idx=start_src_idx,
            end_src_idx=end_src_idx,
            start_price=pending.price,
            end_price=f.price,
        ))
        pending = f

    return pens
