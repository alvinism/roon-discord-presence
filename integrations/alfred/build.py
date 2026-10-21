"""Build dist/Roon-Discord-Presence.alfredworkflow (a zip with info.plist + scripts).

    python integrations/alfred/build.py
"""

import plistlib
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from roon_discord_presence import __version__  # noqa: E402

FILTER, ACTION, NOTIFY = (
    "8A1D2C3B-0001-4F00-9000-000000000001",
    "8A1D2C3B-0002-4F00-9000-000000000002",
    "8A1D2C3B-0003-4F00-9000-000000000003",
)

INFO = {
    "bundleid": "io.github.alvinism.roon-discord-presence.alfred",
    "name": "Roon Discord Presence",
    "description": "Status and controls for roon-discord-presence",
    "category": "Tools",
    "createdby": "roon-discord-presence",
    "webaddress": "https://github.com/alvinism/roon-discord-presence",
    "version": __version__,
    "readme": "Type the keyword (default: rdp) to see what is shown on Discord and to "
              "start, stop or restart the background service.\n\n"
              "Requires the command line tool: uv tool install roon-discord-presence",
    "objects": [
        {
            "uid": FILTER, "type": "alfred.workflow.input.scriptfilter", "version": 3,
            "config": {
                "keyword": "{var:keyword}", "withspace": True, "argumenttype": 1,
                "title": "Roon Discord Presence", "subtext": "Status and controls",
                "runningsubtext": "Checking…", "type": 0, "scriptargtype": 1,
                "script": "./control.sh status", "scriptfile": "", "escaping": 102,
                "queuemode": 1, "queuedelaycustom": 3, "queuedelayimmediatelyinitially": True,
                "queuedelaymode": 0, "alfredfiltersresults": True,
                "alfredfiltersresultsmatchmode": 0, "argumenttrimmode": 0,
                "argumenttreatemptyqueryasnil": True,
            },
        },
        {
            "uid": ACTION, "type": "alfred.workflow.action.script", "version": 2,
            "config": {"script": './control.sh "$1"', "scriptargtype": 1, "type": 0,
                       "scriptfile": "", "escaping": 102, "concurrently": False},
        },
        {
            "uid": NOTIFY, "type": "alfred.workflow.output.notification", "version": 1,
            "config": {"title": "Roon Discord Presence", "text": "{query}",
                       "onlyshowifquerypopulated": True, "lastpathcomponent": False,
                       "removeextension": False},
        },
    ],
    "connections": {
        FILTER: [{"destinationuid": ACTION, "modifiers": 0, "modifiersubtext": "",
                  "vitoclose": False}],
        ACTION: [{"destinationuid": NOTIFY, "modifiers": 0, "modifiersubtext": "",
                  "vitoclose": False}],
    },
    "uidata": {FILTER: {"xpos": 50, "ypos": 50}, ACTION: {"xpos": 300, "ypos": 50},
               NOTIFY: {"xpos": 550, "ypos": 50}},
    "userconfigurationconfig": [
        {"type": "textfield", "variable": "keyword", "label": "Keyword",
         "description": "Keyword that opens the status list", "default": "rdp",
         "config": {"default": "rdp", "placeholder": "rdp", "required": True, "trim": True}},
        {"type": "textfield", "variable": "RDP_BIN", "label": "Path to CLI",
         "description": "Leave empty to look in ~/.local/bin and Homebrew", "default": "",
         "config": {"default": "", "placeholder": "~/.local/bin/roon-discord-presence",
                    "required": False, "trim": True}},
    ],
}


def main():
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / "Roon-Discord-Presence.alfredworkflow"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("info.plist", plistlib.dumps(INFO))
        for name in ("control.sh", "status.js"):
            info = zipfile.ZipInfo(name)
            info.external_attr = 0o755 << 16
            z.writestr(info, (HERE / name).read_bytes())
    print(out)


if __name__ == "__main__":
    main()
