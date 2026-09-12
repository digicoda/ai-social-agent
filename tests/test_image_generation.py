from app.image_generation import IMAGE_SHORTCODES, build_prompt, select_shortcode
from app.profiles import DEFAULT_PROFILE, _merged


def test_image_shortcodes_cover_manual_and_auto_modes():
    assert {"auto", "explainer", "advertisement", "promotion", "marketing", "problem", "solution", "article", "infographic", "social", "case-study"} <= set(IMAGE_SHORTCODES)


def test_ai_auto_selects_visual_mode_from_post():
    assert select_shortcode("How to fix a broken deployment", "This guide explains the steps to diagnose the error.") == "explainer"
    assert select_shortcode("New product offer", "Our campaign promotes a limited discount.") == "advertisement"
    assert select_shortcode("Website error", "The problem is a failed update and the solution is a rollback.") in {"problem", "solution"}


def test_custom_prompt_and_shortcode_are_included():
    prompt = build_prompt("AI workflow", "A practical guide for teams.", "explainer", "Use our dark purple brand style", "16:9")
    assert "Explainer" in prompt
    assert "dark purple brand style" in prompt
    assert "16:9" in prompt


def test_profile_defaults_include_image_controls():
    profile = _merged({})
    assert profile["image_enabled"] is True
    assert profile["image_mode"] == "auto"
    assert profile["image_shortcode"] == "auto"
    assert profile["image_aspect_ratio"] == "1:1"
    assert profile["image_model"] == "gemini-2.5-flash-image"
    assert DEFAULT_PROFILE["image_reference_path"] == ""


def test_profile_manual_image_configuration_is_preserved():
    profile = _merged({"image_mode":"manual","image_shortcode":"advertisement","image_aspect_ratio":"4:5","image_prompt":"Brand campaign","image_model":"gemini-2.5-flash-image"})
    assert profile["image_mode"] == "manual"
    assert profile["image_shortcode"] == "advertisement"
    assert profile["image_aspect_ratio"] == "4:5"
    assert profile["image_prompt"] == "Brand campaign"
