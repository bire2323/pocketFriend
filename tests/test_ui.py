"""Tests for the small UI wrappers.

They exist because these wrappers add arguments of their own (`icon`) on top of
Streamlit's, which is exactly where a name collision hides. A regression here is
invisible until a screen is actually drawn. The stylesheet gets the same
treatment: it targets Streamlit's DOM by test id, so a Streamlit upgrade can
silently turn a rule into dead CSS.
"""

from app.ui import components as ui
from app.ui.theme import stylesheet


class FakeStreamlit:
    """Records what the wrappers forward to Streamlit."""

    def __init__(self):
        self.calls = []

    def button(self, *args, **kwargs):
        self.calls.append(("button", args, kwargs))
        return False

    def download_button(self, *args, **kwargs):
        self.calls.append(("download_button", args, kwargs))
        return False

    def container(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_download_button_takes_data_positionally(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(ui, "st", fake)

    ui.download_button("Save", "the markdown", file_name="plan.md", mime="text/markdown")

    name, args, kwargs = fake.calls[0]
    assert name == "download_button"
    assert args == ("Save", "the markdown")
    assert kwargs["file_name"] == "plan.md"
    assert kwargs["mime"] == "text/markdown"


def test_download_button_icon_does_not_collide_with_data(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(ui, "st", fake)

    ui.download_button("Save", "the markdown", icon="download", key="plan_download")

    _, args, kwargs = fake.calls[0]
    assert args == ("Save", "the markdown")
    assert "icon" not in kwargs, "our icon name must not reach Streamlit's icon"


def test_download_button_without_an_icon(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(ui, "st", fake)

    ui.download_button("Save", "the markdown", key="k")

    assert fake.calls[0][1] == ("Save", "the markdown")


def test_button_forwards_key_and_type(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(ui, "st", fake)

    ui.button("Go", key="go", type="primary", icon="arrow", width="stretch")

    name, args, kwargs = fake.calls[0]
    assert name == "button"
    assert args == ("Go",)
    assert kwargs == {"key": "go", "type": "primary", "width": "stretch"}


class TestStreamlitIcons:
    """Streamlit's Material icons are font ligatures, not SVGs.

    The element literally contains the word "upload". PocketFriend runs offline,
    so the icon font never loads and that word prints next to the button's own
    label - and it only shows up on a real screen.
    """

    def test_ligature_text_is_removed_from_buttons(self):
        css = stylesheet()
        rule = (
            'button[data-testid^="stBaseButton"] [data-testid="stIconMaterial"]'
        )
        assert rule in css
        start = css.index(rule)
        assert "display: none !important" in css[start : start + 200]

    def test_no_rule_enlarges_the_ligature_text(self):
        assert "font-size: 1.15em" not in stylesheet()

    def test_uploader_button_gets_our_own_icon(self):
        css = stylesheet()
        start = css.index('[data-testid="stFileUploaderDropzone"] button::before')
        assert "--i-upload" in css[start : css.index("}", start)]
        assert (
            'button[aria-label="Add files"]' in css
        ), "the icon-only button needs a mask too"

    def test_every_icon_the_app_draws_is_its_own_mask(self):
        css = stylesheet()
        assert "[class*=\"pf-ic-\"] button::before" in css
        assert "--i-upload" in css and "--i-trash" in css and "--i-ask" in css


class TestSidebarToggle:
    def test_both_sidebar_states_are_targeted(self):
        css = stylesheet()
        for test_id in ("stSidebarCollapseButton", "stExpandSidebarButton"):
            assert f'[data-testid="{test_id}"] button' in css, test_id

    def test_no_rule_targets_the_test_id_streamlit_removed(self):
        assert "stSidebarCollapsedControl" not in stylesheet()

    def test_the_hamburger_is_painted_from_the_app_icon_set(self):
        css = stylesheet()
        start = css.index('[data-testid="stSidebarCollapseButton"] button::before')
        assert "--i-menu" in css[start : start + 500]


class TestButtonLabels:
    def test_a_label_cannot_wrap_one_letter_per_row(self):
        assert (
            'button[data-testid^="stBaseButton"] * { white-space: nowrap; }'
            in stylesheet()
        )


class TestDialogStyling:
    def test_the_confirmation_modal_is_styled(self):
        css = stylesheet()
        assert 'div[data-testid="stDialog"]' in css
        assert 'div[data-testid="stDialog"] button[aria-label="Close"]' in css
