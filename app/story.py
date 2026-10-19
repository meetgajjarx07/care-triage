"""The story page: the whole project told in six scenes, in plain words.

Embeds story/index.html, a standalone page with no dependencies, so the same
file can be opened straight from the folder for the video. Arrow keys move
between scenes once the frame has focus (click it first).
"""

import streamlit.components.v1 as components

from ui import ROOT, h, page_header, load_json

STORY = ROOT / "story" / "index.html"


def story():
    run = load_json("run")
    page_header("The story", "The project in six scenes, for someone who does not code. Click the frame, then use the arrow keys. "
                "The same page opens on its own from story/index.html.", run)
    components.html(STORY.read_text(encoding="utf-8"), height=720, scrolling=False)
    h('<div class="note">Everything in the scenes comes from the run in <code>out/</code>: Anita and Muriel are emails E081 and E061, '
      'and the four numbers are the Overview counts. Nothing is a real customer.</div>')
