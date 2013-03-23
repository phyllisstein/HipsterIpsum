import sublime
import sublime_plugin
import threading
import urllib
import json
if int(sublime.version()) >= 3000:
    import HipsterIpsum3.requests as requests
else:
    import requests


def err(theError):
    print("[Hipster Ipsum: " + theError + "]")


class HipsterIpsumCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        s = sublime.load_settings("Hipster Ipsum.sublime-settings")
        defaultParas = s.get("paragraphs", 1)
        ipsumType = s.get("ipsum_type", "hipster-centric")
        useHTML = "false" if s.get("html", False) == False else "true"

        selections = self.view.sel()
        threads = []
        passedThreads = 0
        skippedThreads = 0
        for theSelection in selections:
            theSubstring = self.view.substr(theSelection)
            if len(theSubstring) == 0:
                newThread = HipsterIpsumAPICall(theSelection, defaultParas, ipsumType, useHTML, "")
                threads.append(newThread)
                newThread.start()
                passedThreads += 1
            else:
                try:
                    parasHere = int(theSubstring)
                except ValueError:
                    newThread = HipsterIpsumAPICall(theSelection, defaultParas, ipsumType, useHTML, theSubstring)
                    threads.append(newThread)
                    newThread.start()
                    passedThreads += 1
                else:
                    if parasHere < 1:
                        err("%i is too few paragraphs." % parasHere)
                        err("Select a number between 1 and 99.")
                        sublime.status_message("Hipster Ipsum: Too few paragraphs (%i)." % parasHere)
                        skippedThreads += 1
                    elif parasHere > 99:
                        err("%i is too many paragraphs." % parasHere)
                        err("Select a number between 1 and 99.")
                        sublime.status_message("Hipster Ipsum: Too many paragraphs (%i)." % parasHere)
                        skippedThreads += 1
                    else:
                        newThread = HipsterIpsumAPICall(theSelection, parasHere, ipsumType, useHTML, theSubstring)
                        threads.append(newThread)
                        newThread.start()
                        passedThreads += 1
        if passedThreads > 0:
            self.view.sel().clear()
            self.manageThreads(threads)
        else:
            sublime.status_message("Hipster Ipsum: No authentic selections.")
            err("Skipped %i selections." % skippedThreads)

    def manageThreads(self, theThreads, offset=0, i=0, direction=1):
        next_threads = []
        for thread in theThreads:
            if thread.is_alive():
                next_threads.append(thread)
                continue
            if thread.result == False:
                continue
            offset = self.replace(thread, offset)
        theThreads = next_threads

        if len(theThreads):
            before = i % 8
            after = 7 - before
            if not after:
                direction = -1
            if not before:
                direction = 1
            i += direction
            self.view.set_status("hipster_ipsum", "Gentrifying... [%s=%s]" % (" " * before, " " * after))

            sublime.set_timeout(lambda: self.manageThreads(theThreads, offset, i, direction), 100)
            return

        self.view.erase_status("hipster_ipsum")
        selections = len(self.view.sel())
        sublime.status_message("%s area%s gentrified." % (selections, '' if selections == 1 else 's'))

    def replace(self, theThread, offset):
        selection = theThread.selection
        original = theThread.original
        result = theThread.result

        if offset:
            selection = sublime.Region(selection.begin() + offset, selection.end() + offset)

        result = self.normalize_line_endings(result)
        self.view.run_command("hipster_ipsum_replace", {"begin": selection.begin(), "end": selection.end(), "data": result})
        endpoint = selection.begin() + len(result)
        self.view.sel().add(sublime.Region(endpoint, endpoint))

        return offset + len(result) - len(original)

    def normalize_line_endings(self, string):
        string = string.replace('\n', '\n\n')
        string = string.replace('\r\n', '\n').replace('\r', '\n')
        line_endings = self.view.settings().get('default_line_ending')
        if line_endings == 'windows':
            string = string.replace('\n', '\r\n')
        elif line_endings == 'mac':
            string = string.replace('\n', '\r')
        return string


class HipsterIpsumAPICall(threading.Thread):
    def __init__(self, theSelection, numParagraphs, ipsumType, useHTML, originalString):
        self.selection = theSelection
        self.paragraphs = numParagraphs
        self.ipsumType = ipsumType
        self.useHTML = useHTML
        self.original = originalString
        self.result = None
        threading.Thread.__init__(self)

    def run(self):
        params = {"paras": self.paragraphs, "type": self.ipsumType, "html": self.useHTML}
        
        try:
            r = requests.get("http://hipsterjesus.com/api/", params=params)
        except Exception as e:
            err("Exception: %s" % e)
            self.result = False

        data = r.json()
        self.result = data["text"]

class HipsterIpsumReplaceCommand(sublime_plugin.TextCommand):
    def run(self, edit, begin, end, data):
        a = long(begin) if int(sublime.version()) < 3000 else begin
        b = long(end) if int(sublime.version()) < 3000 else end
        region = sublime.Region(a, b)
        self.view.replace(edit, region, data)
