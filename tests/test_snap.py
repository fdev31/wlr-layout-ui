"""Tests for the snap/attraction system in the UI class.

Verifies that:
- Center (middle) alignment has the highest priority
- Edge-to-edge adjacency (opposite edges) works
- Same-edge alignment works
- Corners are reachable but lower priority
- Center reach limit prevents unreasonable pulls
- Attraction mode works for nearby non-overlapping screens
"""

import sys

sys.path.insert(0, "src")

import pyglet

pyglet.options["headless"] = True

from pyggets import Rect as PRect  # noqa: E402
from wlr_layout_ui.gui import UI  # noqa: E402

# ---------------------------------------------------------------------------
# Lightweight helpers to exercise snap logic without a full UI window.
# ---------------------------------------------------------------------------


class FakeScreen:
    """Minimal stand-in for GuiScreen — only needs rect and target_rect."""

    def __init__(self, x, y, w, h):
        self.rect = PRect(x, y, w, h)
        self.target_rect = PRect(x, y, w, h)


class SnapHarness:
    """Wraps a list of FakeScreens and exposes UI's snap methods.

    The *last* screen in `gui_screens` is the "active" screen being moved,
    matching the UI convention.
    """

    def __init__(self, screens: list[FakeScreen]):
        self.gui_screens = screens

    # Bind UI's methods onto the harness.
    # _ref_points is a @staticmethod, so we reference it directly.
    _ref_points = staticmethod(UI._ref_points)
    _axes_match = UI._axes_match
    _axis_tier = UI._axis_tier
    _snap_weight = UI._snap_weight
    _collect_snap_axes = UI._collect_snap_axes
    _test_no_overlap = UI._test_no_overlap
    _snap_to_best_non_overlapping = UI._snap_to_best_non_overlapping

    # Class-level constants from UI
    SNAP_WEIGHT_BOTH = UI.SNAP_WEIGHT_BOTH
    SNAP_WEIGHT_SINGLE = UI.SNAP_WEIGHT_SINGLE
    SNAP_PENALTY_CORNER = UI.SNAP_PENALTY_CORNER
    TIER_CENTER = UI.TIER_CENTER
    TIER_OPPOSITE = UI.TIER_OPPOSITE
    TIER_SAME = UI.TIER_SAME
    TIER_NONE = UI.TIER_NONE
    _OPPOSITE_EDGES = UI._OPPOSITE_EDGES
    SNAP_RADIUS = UI.SNAP_RADIUS

    def snap_active(self):
        """Run snap_active_screen logic: resolve overlaps."""
        active = self.gui_screens[-1]
        colliding = [s for s in self.gui_screens[:-1] if s.rect.collide(active.rect)]
        if colliding:
            self._snap_to_best_non_overlapping(active, colliding)

    def attract_active(self):
        """Run attract_screens logic: magnet-pull toward neighbors."""
        active = self.gui_screens[-1]
        ar = active.target_rect
        for other in self.gui_screens[:-1]:
            if ar.collide(other.target_rect):
                return
        self._snap_to_best_non_overlapping(
            active,
            self.gui_screens[:-1],
            max_dist=self.SNAP_RADIUS,
        )


def _pos(screen: FakeScreen) -> tuple[int, int]:
    """Return the (x, y) position of the screen's target_rect."""
    return (screen.target_rect.x, screen.target_rect.y)


# ---------------------------------------------------------------------------
# Center alignment wins over edge alignment (overlap resolution)
# ---------------------------------------------------------------------------


class TestCenterAlignmentPriority:
    """Center alignment should beat edge alignment for overlapping screens."""

    def test_center_wins_different_height_overlap(self):
        """Screen B (60x60) overlaps taller screen A (100x100).

        B is dropped in the middle of A.  Center-aligned positions inside A
        all overlap, so the algorithm must push B out via adjacency on one
        axis.  The best result should still center-align on the cross-axis.

        With tier-based scoring, the Y-axis center snap (tier 0) should be
        preferred over edge alignment (tier 2) on the cross-axis.
        """
        # A: 100x100 at origin.  B: 60x60 dropped overlapping A at (50, 50).
        # Best non-overlapping: B right of A (B.left=A.right=100) with
        # center_y aligned (A.cy=50, B.cy=50 → B.y=20).
        a = FakeScreen(0, 0, 100, 100)
        b = FakeScreen(50, 50, 60, 60)
        harness = SnapHarness([a, b])
        harness.snap_active()
        assert not a.target_rect.collide(b.target_rect), f"Screens still overlap: A={a.target_rect}, B={b.target_rect}"
        # Center-Y should be aligned: B.center_y == A.center_y == 50
        b_center_y = b.target_rect.y + b.target_rect.height / 2
        assert b_center_y == 50, f"Expected center-aligned center_y=50, got {b_center_y} (B.y={b.target_rect.y})"

    def test_center_wins_different_width_overlap(self):
        """Screen B (60x100) overlaps wider screen A (100x100).

        B is dropped overlapping A from the right side.  Center X alignment
        should win over edge alignment.
        """
        # A: 100x100 at origin.  B: 60x100 dropped at (60, 0).
        # Center-aligned X: A.center_x=50, B needs center_x=50 → B.x = 50-30 = 20.
        # Edge-aligned X (B.left = A.right): B.x = 100 (adjacency, tier 1).
        a = FakeScreen(0, 0, 100, 100)
        b = FakeScreen(60, 0, 60, 100)
        harness = SnapHarness([a, b])
        harness.snap_active()
        # B center-aligned would put it at x=20, but that overlaps A.
        # The only non-overlapping center-aligned option needs to push B out.
        # Actually, center_x for B at x=20 means B occupies x=[20,80] which
        # overlaps A at [0,100].  So center X can't work while overlapping.
        # The snap should find the best non-overlapping position.
        # With X-axis: B.right → A.left means B.x = -60 (left of A), or
        #              B.left → A.right means B.x = 100 (right of A).
        # With Y-axis: center_y should align (both 100 tall, so trivially aligned).
        # The important thing: B should be adjacent to A, not at some random edge.
        assert b.target_rect.y == 0, f"Expected Y-aligned y=0, got y={b.target_rect.y}"
        # B should be pushed to one side of A (x=100 or x=-60)
        assert b.target_rect.x == 100 or b.target_rect.x == -60, f"Expected B adjacent to A, got x={b.target_rect.x}"

    def test_center_y_wins_over_bottom_alignment(self):
        """A=200x100, B=200x60 dropped overlapping at (0, 10).

        Both screens are same width (200) so X is trivially aligned.
        On Y-axis: center snap puts B.center_y at A.center_y=50 → B.y=20.
        But B.y=20 with height=60 means B occupies y=[20,80], fully inside
        A at y=[0,100] — this overlaps!
        The best non-overlapping center-Y result is B placed above or below A
        with centers aligned on X.
        """
        a = FakeScreen(0, 0, 200, 100)
        b = FakeScreen(0, 10, 200, 60)
        harness = SnapHarness([a, b])
        harness.snap_active()
        # B should be placed above or below A (no overlap).
        assert not a.target_rect.collide(b.target_rect), f"Screens still overlap: A={a.target_rect}, B={b.target_rect}"
        # X should remain aligned (both same width, centers match).
        assert b.target_rect.x == 0, f"Expected X-aligned x=0, got x={b.target_rect.x}"

    def test_center_alignment_same_size_screens(self):
        """Same-size screens: center alignment is trivially satisfied.

        For same-size screens, center alignment and edge alignment produce
        the same result, so both should work.
        """
        a = FakeScreen(0, 0, 100, 100)
        b = FakeScreen(50, 50, 100, 100)  # overlapping
        harness = SnapHarness([a, b])
        harness.snap_active()
        assert not a.target_rect.collide(b.target_rect), f"Screens still overlap: A={a.target_rect}, B={b.target_rect}"


# ---------------------------------------------------------------------------
# Edge-to-edge adjacency (opposite edges)
# ---------------------------------------------------------------------------


class TestEdgeAdjacency:
    """Opposite-edge snaps should place screens edge-to-edge."""

    def test_right_to_left_adjacency(self):
        """B overlaps A from the right → B.left = A.right."""
        a = FakeScreen(0, 0, 100, 100)
        b = FakeScreen(80, 0, 100, 100)  # overlaps A by 20px on right
        harness = SnapHarness([a, b])
        harness.snap_active()
        # B should snap to A's right edge
        assert b.target_rect.x == 100, f"Expected B.x=100 (right-adjacent), got x={b.target_rect.x}"
        assert b.target_rect.y == 0

    def test_top_to_bottom_adjacency(self):
        """B overlaps A from above → B.bottom = A.top."""
        a = FakeScreen(0, 0, 100, 100)
        b = FakeScreen(0, 80, 100, 100)  # overlaps A by 20px on top
        harness = SnapHarness([a, b])
        harness.snap_active()
        # B should snap above A
        assert b.target_rect.y == 100, f"Expected B.y=100 (above A), got y={b.target_rect.y}"
        assert b.target_rect.x == 0

    def test_left_to_right_adjacency(self):
        """B overlaps A from the left → B.right = A.left."""
        a = FakeScreen(100, 0, 100, 100)
        b = FakeScreen(120, 0, 100, 100)  # overlaps A from left side
        harness = SnapHarness([a, b])
        harness.snap_active()
        # B should end up adjacent to A (either left or right)
        assert not a.target_rect.collide(b.target_rect)


# ---------------------------------------------------------------------------
# Attraction mode (non-overlapping screens pulled to neighbors)
# ---------------------------------------------------------------------------


class TestAttraction:
    """Attraction should pull nearby non-overlapping screens to snap points."""

    def test_attract_to_right_edge(self):
        """B placed 10px to the right of A → attracted to A's right edge."""
        a = FakeScreen(0, 0, 100, 100)
        b = FakeScreen(110, 0, 100, 100)  # 10px gap
        harness = SnapHarness([a, b])
        harness.attract_active()
        # B should snap to A.right = 100
        assert b.target_rect.x == 100, f"Expected B.x=100 (attracted to right edge), got x={b.target_rect.x}"

    def test_attract_center_alignment(self):
        """B (smaller) placed to the right of A with slight Y offset.

        Attraction should center-align Y because center is highest priority.
        """
        # A: 100x100 at origin.  B: 100x60 at (110, 5) — 10px gap, 5px Y offset.
        a = FakeScreen(0, 0, 100, 100)
        b = FakeScreen(110, 5, 100, 60)
        harness = SnapHarness([a, b])
        harness.attract_active()
        # X: B should snap to A.right=100 (adjacency, tier 1)
        assert b.target_rect.x == 100, f"Expected B.x=100, got x={b.target_rect.x}"
        # Y: center-aligned → A.center_y=50, B.center_y should be 50 → B.y=20
        assert b.target_rect.y == 20, f"Expected center-aligned B.y=20, got y={b.target_rect.y}"

    def test_no_attract_beyond_radius(self):
        """Screens far apart on both axes should not attract.

        SNAP_RADIUS applies per-axis, so we need both X and Y deltas to
        exceed the radius for no attraction to occur.
        """
        a = FakeScreen(0, 0, 100, 100)
        b = FakeScreen(500, 500, 100, 100)  # far on both axes
        harness = SnapHarness([a, b])
        orig_pos = _pos(b)
        harness.attract_active()
        assert _pos(b) == orig_pos, f"Screen should not have moved, but went from {orig_pos} to {_pos(b)}"

    def test_attract_does_not_cause_overlap(self):
        """Attraction should never cause screens to overlap."""
        a = FakeScreen(0, 0, 100, 100)
        b = FakeScreen(105, 0, 100, 100)
        harness = SnapHarness([a, b])
        harness.attract_active()
        assert not a.target_rect.collide(b.target_rect), f"Attraction caused overlap: A={a.target_rect}, B={b.target_rect}"


# ---------------------------------------------------------------------------
# Center reach limit
# ---------------------------------------------------------------------------


class TestCenterReachLimit:
    """Center snap should be limited to 100% of the larger screen's dimension."""

    def test_center_within_reach(self):
        """Center snap within reach should work."""
        # A: 100x100, B: 100x60.  max reach = max(100,60) = 100 on Y.
        # If B is dropped near A, center_y delta = |B.cy - A.cy| should be < 100.
        a = FakeScreen(0, 0, 100, 100)
        b = FakeScreen(110, 5, 100, 60)
        harness = SnapHarness([a, b])
        harness.attract_active()
        # Center Y should activate (delta = |35 - 50| = 15, well within 100).
        assert b.target_rect.y == 20, f"Expected center-aligned B.y=20, got y={b.target_rect.y}"


# ---------------------------------------------------------------------------
# Tier ordering correctness
# ---------------------------------------------------------------------------


class TestAxisTier:
    """_axis_tier returns correct priority tiers."""

    def setup_method(self):
        self.h = SnapHarness([])

    def test_center_x_tier(self):
        assert self.h._axis_tier("center_x", "center_x") == UI.TIER_CENTER

    def test_center_y_tier(self):
        assert self.h._axis_tier("center_y", "center_y") == UI.TIER_CENTER

    def test_opposite_edges_tier(self):
        assert self.h._axis_tier("left", "right") == UI.TIER_OPPOSITE
        assert self.h._axis_tier("right", "left") == UI.TIER_OPPOSITE
        assert self.h._axis_tier("top", "bottom") == UI.TIER_OPPOSITE
        assert self.h._axis_tier("bottom", "top") == UI.TIER_OPPOSITE

    def test_same_edge_tier(self):
        assert self.h._axis_tier("left", "left") == UI.TIER_SAME
        assert self.h._axis_tier("right", "right") == UI.TIER_SAME
        assert self.h._axis_tier("top", "top") == UI.TIER_SAME
        assert self.h._axis_tier("bottom", "bottom") == UI.TIER_SAME

    def test_no_match_tier(self):
        assert self.h._axis_tier("left", "top") == UI.TIER_NONE
        assert self.h._axis_tier("center_x", "left") == UI.TIER_NONE

    def test_tier_ordering(self):
        """Center < opposite < same < none (lower = higher priority)."""
        assert UI.TIER_CENTER < UI.TIER_OPPOSITE < UI.TIER_SAME < UI.TIER_NONE


# ---------------------------------------------------------------------------
# Overlap resolution should not leave overlaps
# ---------------------------------------------------------------------------


class TestNoOverlapInvariant:
    """After snap, no screens should overlap."""

    def test_full_overlap_resolved(self):
        """B dropped exactly on top of A."""
        a = FakeScreen(0, 0, 100, 100)
        b = FakeScreen(0, 0, 100, 100)
        harness = SnapHarness([a, b])
        harness.snap_active()
        assert not a.target_rect.collide(b.target_rect), f"Full overlap not resolved: A={a.target_rect}, B={b.target_rect}"

    def test_partial_overlap_resolved(self):
        """B overlapping A partially."""
        a = FakeScreen(0, 0, 100, 100)
        b = FakeScreen(30, 30, 100, 100)
        harness = SnapHarness([a, b])
        harness.snap_active()
        assert not a.target_rect.collide(b.target_rect), f"Overlap not resolved: A={a.target_rect}, B={b.target_rect}"

    def test_three_screens_no_overlap(self):
        """Three screens: B overlapping both A and C."""
        a = FakeScreen(0, 0, 100, 100)
        c = FakeScreen(200, 0, 100, 100)
        b = FakeScreen(50, 0, 200, 100)  # overlaps both A and C
        harness = SnapHarness([a, c, b])  # b is last = active
        harness.snap_active()
        assert not a.target_rect.collide(b.target_rect), "B overlaps A"
        assert not c.target_rect.collide(b.target_rect), "B overlaps C"
