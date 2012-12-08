import sublime
import sublime_plugin
import threading
import urllib
# import urlparse
import json
import urllib2


def err(theError):
    print "[Hipster Ipsum: " + theError + "]"


class hipsterIpsumCommand(sublime_plugin.TextCommand):
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
            edit = self.view.begin_edit("hipster_ipsum")
            self.manageThreads(edit, threads)
        else:
            sublime.status_message("Hipster Ipsum: No authentic selections.")
            err("Skipped %i selections." % skippedThreads)

    def manageThreads(self, theEdit, theThreads, offset=0, i=0, direction=1):
        next_threads = []
        for thread in theThreads:
            if thread.is_alive():
                next_threads.append(thread)
                continue
            if thread.result == False:
                continue
            offset = self.replace(theEdit, thread, offset)
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

            sublime.set_timeout(lambda: self.manageThreads(theEdit, theThreads, offset, i, direction), 100)
            return

        self.view.end_edit(theEdit)
        self.view.erase_status("hipster_ipsum")
        selections = len(self.view.sel())
        sublime.status_message("%s area%s gentrified." % (selections, '' if selections == 1 else 's'))

    def replace(self, theEdit, theThread, offset):
        selection = theThread.selection
        original = theThread.original
        result = theThread.result

        if offset:
            selection = sublime.Region(selection.begin() + offset, selection.end() + offset)

        result = self.normalize_line_endings(result)
        self.view.replace(theEdit, selection, result)
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
        query = urllib.urlencode(params)
        uriString = "http://hipsterjesus.com/api/?" + query
        try:
            connection = urllib2.urlopen(uriString)
            data = json.load(connection)
            self.result = data["text"]
            return
        except urllib2.HTTPError as e:
            error = "HTTP error " + str(e.code)
            err(error)
        except urllib2.URLError as e:
            error = "URL error " + str(e.reason)
            err(error)

        self.result = False
