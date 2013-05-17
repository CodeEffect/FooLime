import sublime
import sublime_plugin
import os
import re
import subprocess
import time

# Available switches:
#   /add <list-of-files> - appends the specified files to the current playlist
#       instead of replacing the playlist content and playing them immediately
#   /immediate - bypasses the "please wait" dialog when adding files
#   /play, /pause, /playpause, /prev, /next, /rand, /stop - playback controls
#   /exit - exits foobar2000
#   /show, /hide - shows or hides the main foobar2000 window
#   /config - opens the Preferences dialog
#   /command:<menu command> - invokes the specified main menu command
#   /playlist_command:<context menu command> - invokes the specified context
#       menu command on current playlist selection
#   /playing_command:<context menu command> - invokes the specified context
#       menu command on currently played track
#   /context_command:<context menu command> <files> - invokes the specified
#       context menu command on the specified files


class FooLime(sublime_plugin.TextCommand):

    settingFile = "FooLime.sublime-settings"
    fooPath = "C:\\Program Files (x86)\\foobar2000\\foobar2000.exe"
    settings = False
    playing = False
    folder = ""
    items = []

    def run(self, edit, action=None, alarmId=None):
        action = str(action).lower()

        if action == "none" or action == "choose":
            self.selectTunes()
        if action == "control":
            self.control()

    def selectTunes(self):
        self.listMusic(self.folder)
        self.addFolderOptions()
        self.show_quick_panel(self.items, self.handleSelect)

    def handleSelect(self, selection):
        if selection is -1:
            return

        if selection is 0:
            # Up a dir
            if not os.path.isdir(self.folder[0:self.folder.rfind(os.sep)]):
                return sublime.status_message("Unable to go up any further!")
            self.folder = self.folder[0:self.folder.rfind(os.sep)]
            self.getSettings().set("current_folder", self.folder)
            sublime.save_settings(self.settingFile)
            self.listMusic(self.folder)
            self.addFolderOptions()
            self.show_quick_panel(self.items, self.handleSelect)
        elif selection is 1:
            # play in order
            self.playFile(self.folder)
        elif selection is 2:
            # play randomly
            self.playFile(self.folder, random=True)
        elif selection is 3:
            # Home folder
            self.folder = self.getSettings().get(
                "home_folder",
                os.path.dirname(os.path.abspath(__file__))
            )
            self.listMusic(self.folder)
            self.addFolderOptions()
            self.show_quick_panel(self.items, self.handleSelect)
        else:
            # a file / folder from self.items has been selected
            selected = self.items[selection]
            if selected[1] == "Folder":
                self.folder = os.path.join(self.folder, selected[0])
                self.getSettings().set("current_folder", self.folder)
                sublime.save_settings(self.settingFile)
                self.listMusic(self.folder)
                self.addFolderOptions()
                self.show_quick_panel(self.items, self.handleSelect)
            else:
                self.playFile(os.path.join(self.folder, selected[0]))

    def control(self):
        self.items = [
            "Pause / play",
            "Prev track",
            "Next track",
            "Quit",
            "Volume up",
            "Volume down",
        ]
        self.show_quick_panel(self.items, self.handleControl)

    def handleControl(self, selection):
        if selection is -1:
            return

        cmd = ""
        selected = self.items[selection]

        if selected == "Prev track":
            cmd = "/prev"
            self.items = [
                "Prev track",
                "Next track",
                "Pause / play",
                "Quit",
                "Volume up",
                "Volume down"
            ]
        elif selected == "Next track":
            cmd = "/next"
            self.items = [
                "Next track",
                "Prev track",
                "Pause / play",
                "Quit",
                "Volume up",
                "Volume down"
            ]
        elif selected == "Volume up":
            cmd = "/command:Up"
            self.items = [
                "Volume up",
                "Volume down",
                "Pause / play",
                "Prev track",
                "Next track",
                "Quit"
            ]
        elif selected == "Volume down":
            cmd = "/command:Down"
            self.items = [
                "Volume down",
                "Volume up",
                "Pause / play",
                "Prev track",
                "Next track",
                "Quit"
            ]
        elif selected == "Pause / play":
            cmd = "/playpause"
            self.items = []
        elif selected == "Quit":
            cmd = "/exit"
            self.items = []

        if cmd:
            subprocess.Popen([
                self.getSettings().get("foo_path", self.fooPath),
                cmd
            ])
        if self.items:
            self.show_quick_panel(self.items, self.handleControl)

    def playFile(self, file, random=False):
        self.playing = subprocess.Popen([
            self.getSettings().get("foo_path", self.fooPath),
            "/play",
            file
        ])
        time.sleep(0.1)
        subprocess.Popen([
            self.getSettings().get("foo_path", self.fooPath),
            "/hide"
        ])
        if random:
            time.sleep(0.1)
            subprocess.Popen([
                self.getSettings().get("foo_path", self.fooPath),
                "/rand"
            ])

    def listMusic(self, path):
        if not path:
            path = self.getSettings().get(
                "current_folder",
                None
            )
        if not path or not os.path.isdir(path):
            path = self.getSettings().get(
                "home_folder",
                os.path.dirname(os.path.abspath(__file__))
            )
        if "%" in path:
            path = os.path.expandvars(path)
        self.items = []
        if path[-1] == os.sep:
            path = path[-1]
        if len(path) is 2 and path[1] is ":":
            path += "\\"
            os.chdir(path)
        self.folder = path
        for f in os.listdir(path):
            if os.path.isdir(os.path.join(path, f)):
                self.items.append([f, "Folder"])
            pattern = re.compile("(mp3|wav|ogg)$")
            if pattern.search(f):
                self.items.append([f, "%s file" % f[-3:]])

    def addFolderOptions(self):
        # Add other default options (play folder, play random)
        self.items.insert(0, [
            "Home folder",
            str(self.getSettings().get("home_folder"))
        ])
        self.items.insert(0, ["Play folder randomly", self.folder])
        self.items.insert(0, ["Play folder", self.folder])
        self.items.insert(0, [".. Folder up", self.folder])

    def getSettings(self):
        if not self.settings:
            self.settings = sublime.load_settings(self.settingFile)
        return self.settings

    def show_quick_panel(self, options, done):
        sublime.set_timeout(
            lambda: self.view.window().show_quick_panel(options, done),
            10
        )
