from apps.core.services.text import plain_text


def test_plain_text() -> None:
    assert plain_text("  Just text.  ") == "Just text."
    assert plain_text("<b>Rally!</b>\n\nGo &amp; win.") == "Rally!\n\nGo & win."
    assert plain_text("Modes:<ul><li>Story</li>\n<li>Versus</li></ul>Done") == (
        "Modes:\n\n• Story\n• Versus\n\nDone"
    )
    assert plain_text("One<br>Two<br/>Three<p>Four</p>") == "One\nTwo\nThree\n\nFour"
    # Comparisons are no tags.
    assert plain_text("1 < 2 and 3 > 2") == "1 < 2 and 3 > 2"
