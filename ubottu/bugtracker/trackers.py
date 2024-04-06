# -*- Encoding: utf-8 -*-
###
# Copyright (c) 2005-2007 Dennis Kaarsemaker
# Copyright (c) 2008-2010 Terence Simpson
# Copyright (c) 2017-     Krytarik Raido
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
###


import sys, os, re, json, base64
import xml.dom.minidom as minidom
from email.parser import FeedParser
from pysimplesoap.client import SoapClient

def _getnodetxt(node):
    L = []
    for childnode in node.childNodes:
        if childnode.nodeType == childnode.TEXT_NODE:
            L.append(childnode.data)
    if not L:
        raise ValueError("No text nodes")
    val = ''.join(L)
    if node.hasAttribute('encoding'):
        encoding = node.getAttribute('encoding')
        if encoding == 'base64':
            try:
                val = decodeBase64(val)
            except:
                val = 'Cannot convert bug data from base64.'
    return utils.web.htmlToText(val, tagReplace='')

def _getnodeattr(node, attr):
    if node.hasAttribute(attr):
        val = node.getAttribute(attr)
    else:
        raise ValueError("No such attribute")
    return utils.web.htmlToText(val, tagReplace='')

# Work around PySimpleSOAP still lacking Base64 support
def checkBase64(text):
    if re.match(r'^[a-zA-Z0-9+/]+={0,2}$', text) and len(text) % 4 == 0:
        return True
    return False

def decodeBase64(text):
    if sys.version_info < (3,0):
        return base64.b64decode(text)
    else:
        return base64.b64decode(text).decode('utf-8')

class BugtrackerError(Exception):
    """A bugtracker error"""
    pass

class BugNotFoundError(Exception):
    """Pity, bug isn't there"""
    pass

cvere = re.compile(r'<th[^>]*>Description</th>.*?<td[^>]*>\s*(?P<cve>.*?)\s*</td>', re.I | re.DOTALL)
cverre = re.compile(r'<h2[^>]*>\s*(?P<cverr>.*?)\s*</h2>', re.I | re.DOTALL)
# Define CVE tracker
class CVE:
    def get_bug(self, channel, cveid, do_url=True):
        url = "https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-%s" % cveid
        try:
            cvedata = utils.web.getUrl(url).decode('utf-8')
        except Exception as e:
            raise BugtrackerError('Could not get CVE data: %s (%s)' % (e, url))
        match = cvere.search(cvedata)
        if match:
            cve = utils.web.htmlToText(match.group('cve'), tagReplace='')
            desc_max = 450 - len(channel)
            if do_url:
                desc_max -= len(url) + 3
            if len(cve) > desc_max:
                cve = cve[:desc_max-3] + '...'
            if do_url:
                cve += ' <%s>' % url
            return cve
        else:
            match = cverre.search(cvedata)
            if match:
                cverr = utils.web.htmlToText(match.group('cverr'), tagReplace='')
                if "Couldn't find" in cverr:
                    raise BugNotFoundError
                return cverr
            else:
                raise BugtrackerError('Could not parse CVE data (%s)' % url)

# Define all bugtrackers
class IBugtracker:
    def __init__(self, name=None, url=None, description=None, trackertype=None, aliases=[]):
        self.name        = name
        self.url         = url
        self.description = description
        self.trackertype = trackertype
        self.aliases     = set(aliases)
        self.errget      = 'Could not get data from %s: %s (%s)'
        self.errparse    = 'Could not parse data from %s: %s (%s)'
        self.errparseno  = 'Could not parse data from %s (%s)'

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.url)

    def __cmp__(self, other): # used implicitly in Bugtracker.is_ok()
        return cmp(hash(self), hash(other))

class Bugzilla(IBugtracker):
    def get_tracker(self, url):
        try:
            match = re.match(r'(?P<url>(?P<desc>[^\s/]+)\S*)/show_bug\.cgi', url)
            desc  = match.group('desc')
            name  = desc.lower()
            url   = 'https://%s' % match.group('url')
            return Bugzilla(name, url, desc, 'bugzilla')
        except:
            pass

    def get_bug(self, bugtype, bugid):
        url = "%s/rest/bug/%s" % (self.url, bugid)
        try:
            bugjson = utils.web.getUrl(url).decode('utf-8')
            if re.search(r'<div id="error_msg"[^>]*>\s*The REST Interface feature is not\s+available in this Bugzilla.\s*</div>',
                         bugjson):
                return self.get_bug_old(bugtype, bugid)
            bug = json.loads(bugjson)['bugs'][0]
        except Exception as e:
            # For old-stable Bugzilla
            if 'HTTP Error 404' in str(e):
                return self.get_bug_old(bugtype, bugid)
            raise BugtrackerError(self.errget % (self.description, e, url))
        try:
            status = bug['status']
            if bug['resolution']:
                status += ': %s' % bug['resolution']
            if bug['assigned_to_detail']:
                assignee = bug['assigned_to_detail']['real_name']
                if not assignee:
                    assignee = bug['assigned_to_detail']['name']
            else:
                assignee = ''
            return (bugid, bug['product'], bug['summary'], bug['severity'], status, assignee,
                    "%s/show_bug.cgi?id=%s" % (self.url, bugid), [], [])
        except Exception as e:
            raise BugtrackerError(self.errparse % (self.description, e, url))

    def get_bug_old(self, bugtype, bugid): # Deprecated
        url = "%s/show_bug.cgi?id=%s&ctype=xml" % (self.url, bugid)
        try:
            bugxml = utils.web.getUrl(url)
            zilladom = minidom.parseString(bugxml)
        except Exception as e:
            raise BugtrackerError(self.errget % (self.description, e, url))
        bug_n = zilladom.getElementsByTagName('bug')[0]
        if bug_n.hasAttribute('error'):
            errtxt = bug_n.getAttribute('error')
            if errtxt in ('NotFound', 'InvalidBugId'):
                raise BugNotFoundError
            s = 'Could not get %s bug #%s: %s' % (self.description, bugid, errtxt)
            raise BugtrackerError(s)
        try:
            title = _getnodetxt(bug_n.getElementsByTagName('short_desc')[0])
            status = _getnodetxt(bug_n.getElementsByTagName('bug_status')[0])
            try:
                status = "%s: %s" % (status, _getnodetxt(bug_n.getElementsByTagName('resolution')[0]))
            except:
                pass
            product = _getnodetxt(bug_n.getElementsByTagName('product')[0])
            severity = _getnodetxt(bug_n.getElementsByTagName('bug_severity')[0])
            try:
                assignee = _getnodeattr(bug_n.getElementsByTagName('assigned_to')[0], 'name')
            except:
                try:
                    assignee = _getnodetxt(bug_n.getElementsByTagName('assigned_to')[0])
                except:
                    assignee = ''
        except Exception as e:
            raise BugtrackerError(self.errparse % (self.description, e, url))
        return (bugid, product, title, severity, status, assignee, "%s/show_bug.cgi?id=%s" % (self.url, bugid), [], [])

class Launchpad(IBugtracker):
    statuses = ("Unknown", "Invalid", "Opinion", "Won't Fix", "Fix Released", "Fix Committed", "New",
                "Incomplete", "Confirmed", "Triaged", "In Progress")
    severities = ("Unknown", "Undecided", "Wishlist", "Low", "Medium", "High", "Critical")

    def __init__(self, *args, **kwargs):
        IBugtracker.__init__(self, *args, **kwargs)
        self.lp = None

        # A word to the wise:
        # The Launchpad API is much better than the /+text interface we currently use,
        # it's faster and easier to get the information we need.
        # The current /+text interface is not really maintained by Launchpad and most,
        # or all, of the Launchpad developers hate it. For this reason, we are dropping
        # support for /+text in the future in favour of launchpadlib.
        # Terence Simpson (tsimpson) 2010-04-20
        
        try:
            from launchpadlib.launchpad import Launchpad
            cachedir = os.path.join('/tmp/', 'launchpadlib')
            self.lp = Launchpad.login_anonymously("Ubuntu Matrix Bots - Bugtracker", 'production', cachedir, version='devel')
        except ImportError:
            print("Please install python-launchpadlib, the old interface is deprecated")
        except Exception:
            self.lp = None
            print("Unknown exception while accessing the Launchpad API")

    def _parse(self, task): # Deprecated
        parser = FeedParser()
        parser.feed(task)
        return parser.close()

    @classmethod
    def _rank(cls, task):
        try:
            return float('%d.%02d' % (cls.statuses.index(task.status),
                         cls.severities.index(task.importance)))
        except:
            return 0

    @classmethod
    def _rank_old(cls, task):
        try:
            return float('%d.%02d' % (cls.statuses.index(task['status']),
                         cls.severities.index(task['importance'])))
        except:
            return 0

    @classmethod
    def _sort(cls, task1, task2): # Deprecated
        try:
            if task1.status != task2.status:
                if cls.statuses.index(task1.status) < cls.statuses.index(task2.status):
                    return -1
                return 1

            if task1.importance != task2.importance:
                if cls.severities.index(task1.importance) < cls.severities.index(task2.importance):
                    return -1
                return 1
        except:
            return 0
        return 0

    @classmethod
    def _sort_old(cls, task1, task2): # Deprecated
        try:
            if task1['status'] != task2['status']:
                if cls.statuses.index(task1['status']) < cls.statuses.index(task2['status']):
                    return -1
                return 1

            if task1['importance'] != task2['importance']:
                if cls.severities.index(task1['importance']) < cls.severities.index(task2['importance']):
                    return -1
                return 1
        except:
            return 0
        return 0

    def get_bug(self, bugtype, bugid): #TODO: Remove this method and rename 'get_bug_new' to 'get_bug'
        if self.lp:
            return self.get_bug_new(bugtype, bugid)
        return self.get_bug_old(bugtype, bugid)

    def get_bug_new(self, bugtype, bugid): #TODO: Rename this method to 'get_bug'
        try:
            bugdata = self.lp.bugs[int(bugid)]
            if bugdata.private:
                raise BugtrackerError("This bug is private")
            duplicate = []
            dup = bugdata.duplicate_of
            while dup:
                duplicate.append(str(bugdata.id))
                bugdata = dup
                dup = bugdata.duplicate_of

            extinfo = ['affected: %d' % bugdata.users_affected_count_with_dupes]
            extinfo.append('heat: %d' % bugdata.heat)
            tasks = bugdata.bug_tasks

            if tasks.total_size > 1:
                taskdata = sorted(tasks, key=self._rank)[-1]
            else:
                taskdata = tasks[0]

            if taskdata.assignee:
                # In case assignee data is private
                try:
                    assignee = taskdata.assignee.display_name
                except:
                    assignee = ''
            else:
                assignee = ''

        except Exception as e:
            if type(e).__name__ == 'HTTPError': # messy, but saves trying to import lazr.restfulclient.errors.HTPError
                if e.response.status == 404:
                    bugNo = e.content.split()[-1][2:-1] # extract the real bug number
                    if bugNo != bugid: # A duplicate of a private bug, at least we know it exists
                        raise BugtrackerError('Bug #%s is a duplicate of bug #%s, but it is private (%s/bugs/%s)' % (bugid, bugNo, self.url, bugNo))
                    raise BugtrackerError("Bug #%s is private or does not exist (%s/bugs/%s)" % (bugid, self.url, bugid)) # Could be private, could just not exist
                raise BugtrackerError(self.errget % (self.description, e, '%s/bugs/%s' % (self.url, bugid)))
            elif isinstance(e, KeyError):
                raise BugNotFoundError
            raise BugtrackerError(self.errget % (self.description, e, '%s/bugs/%s' % (self.url, bugid)))

        return (bugdata.id, taskdata.bug_target_display_name, bugdata.title, taskdata.importance, taskdata.status,
                assignee, "%s/bugs/%s" % (self.url, bugdata.id), extinfo, duplicate)

    def get_bug_old(self, bugtype, bugid, duplicate=None): # Deprecated
        url = "%s/bugs/%s/+text" % (self.url, bugid)
        try:
            bugdata = utils.web.getUrl(url).decode('utf-8')
        except Exception as e:
            if 'HTTP Error 404' in str(e):
                if duplicate:
                    raise BugtrackerError('Bug #%s is a duplicate of bug #%s, but it is private (%s/bugs/%s)' % (duplicate, bugid, self.url, bugid))
                else:
                    raise BugNotFoundError
            raise BugtrackerError(self.errget % (self.description, e, url))

        try:
            # Split bug data into separate pieces (bug data, task data)
            data    = bugdata.split('\n\nContent-Type:', 1)[0].split('\n\n')
            bugdata = self._parse(data[0])
            if not bugdata['duplicate-of']:
                taskdata = list(map(self._parse, data[1:]))
                if len(taskdata) > 1:
                    taskdata = sorted(taskdata, key=self._rank_old)[-1]
                else:
                    taskdata = taskdata[0]
                if taskdata['assignee']:
                    assignee = re.sub(r' \([^)]*\)$', '', taskdata['assignee'])
                else:
                    assignee = ''
        except Exception as e:
            raise BugtrackerError(self.errparse % (self.description, e, url))

        # Try and find duplicates
        if bugdata['duplicate-of']:
            data = self.get_bug_old(bugtype, bugdata['duplicate-of'], duplicate or bugid)
            data[8].append(bugdata['bug'])
            return data

        return (bugid, taskdata['task'], bugdata['title'], taskdata['importance'], taskdata['status'],
                assignee, "%s/bugs/%s" % (self.url, bugid), [], [])

# <rant>
# Debbugs sucks donkeyballs
# * HTML pages are inconsistent
# * Parsing mboxes gets incorrect with cloning perversions (eg with bug 330000)
# * No sane way of accessing bug reports in a machine readable way (bts2ldap
#   has no search on bugid)
# * The damn thing allow incomplete bugs, eg bugs without severity set. WTF?!?
#
# Fortunately bugs.donarmstrong.com has a SOAP interface which we can use.
# </rant>
class Debbugs(IBugtracker):
    def __init__(self, *args, **kwargs):
        IBugtracker.__init__(self, *args, **kwargs)
        self.soap_client = SoapClient("%s/cgi-bin/soap.cgi" % self.url, namespace="Debbugs/SOAP")

    def get_bug(self, bugtype, bugid):
        url = "%s/cgi-bin/bugreport.cgi?bug=%s" % (self.url, bugid)
        try:
            raw = self.soap_client.get_status(bugs=bugid)
        except Exception as e:
            raise BugtrackerError(self.errget % (self.description, e, url))
        if not hasattr(raw, 'item'):
            raise BugNotFoundError
        try:
            raw = raw.item.value
            title = str(raw.subject)
            if checkBase64(title):
                title = decodeBase64(title)
            if hasattr(raw.fixed_versions, 'item'):
                status = 'Fixed'
            elif str(raw.done):
                status = 'Closed'
            else:
                status = 'Open'
            return (bugid, str(raw.package), title, str(raw.severity), status, '', "%s/%s" % (self.url, bugid), [], [])
        except Exception as e:
            raise BugtrackerError(self.errparse % (self.description, e, url))

class SourceForge(IBugtracker):
    def get_tracker(self, url):
        try:
            match = re.match(r'sourceforge\.net/p/[^\s/]+/(bugs|tickets|feature-requests|patches|todo)', url)
            desc  = match.group(0)
            name  = desc.lower()
            url   = 'https://%s' % desc
            return SourceForge(name, url, desc, 'sourceforge')
        except:
            pass

    def get_bug(self, bugtype, bugid):
        url = "%s/%s/" % (self.url.replace('sourceforge.net', 'sourceforge.net/rest'), bugid)
        try:
            bugjson = utils.web.getUrl(url).decode('utf-8')
            bug = json.loads(bugjson)['ticket']
        except Exception as e:
            raise BugtrackerError(self.errget % (self.description, e, url))
        try:
            product = severity = ''
            if bug['labels']:
                product = bug['labels'][0]
            if '_priority' in bug['custom_fields']:
                severity = 'Pri: %s' % bug['custom_fields']['_priority']
            return (bugid, product, bug['summary'], severity, ': '.join(bug['status'].split('-')),
                     bug['assigned_to'], "%s/%s/" % (self.url, bugid), [], [])
        except Exception as e:
            raise BugtrackerError(self.errparse % (self.description, e, url))

class GitHub(IBugtracker):
    def get_tracker(self, url):
        try:
            match = re.match(r'github\.com/[^\s/]+/[^\s/]+/(issues|pulls?|commits?)', url)
            desc  = match.group(0)
            url   = 'https://%s' % desc
            # Pulls are inconsistent in main and single page URLs
            desc = re.sub(r'/pull$', r'/pulls', desc)
            # Commits are inconsistent in main and single page URLs
            desc = re.sub(r'/commit$', r'/commits', desc)
            name = desc.lower()
            return GitHub(name, url, desc, 'github')
        except:
            pass

    def get_bug(self, bugtype, bugid):
        url = "%s/%s" % (self.url.replace('github.com', 'api.github.com/repos'), bugid)
        # Pulls are inconsistent in web and API URLs
        url = url.replace('/pull/', '/pulls/')
        # Commits are inconsistent in web and API URLs
        url = url.replace('/commit/', '/commits/')
        if bugtype in ('issue', 'bug'):
            url = url.replace('/pulls/', '/issues/')
            url = url.replace('/commits/', '/issues/')
        elif bugtype in ('pull', 'pr', 'merge', 'mr'):
            url = url.replace('/issues/', '/pulls/')
            url = url.replace('/commits/', '/pulls/')
        elif bugtype == 'commit':
            url = url.replace('/issues/', '/commits/')
            url = url.replace('/pulls/', '/commits/')
        try:
            bugjson = utils.web.getUrl(url).decode('utf-8')
            bug = json.loads(bugjson)
        except Exception as e:
            raise BugtrackerError(self.errget % (self.description, e, url))
        try:
            product = '/'.join(self.url.split('/')[-3:-1])
            if '/commits/' not in url:
                title = bug['title']
                if 'merged' in bug and bug['merged']:
                    status = 'Merged'
                else:
                    status = bug['state']
                if bug['assignee']:
                    assignee = bug['assignee']['login']
                else:
                    assignee = ''
            else:
                bugid = bug['sha'][:7]
                title = bug['commit']['message'].split('\n', 1)[0]
                status = ''
                assignee = ''
            return (bugid, product, title, '', status, assignee, bug['html_url'], [], [])
        except Exception as e:
            raise BugtrackerError(self.errparse % (self.description, e, url))

class GitLab(IBugtracker):
    def get_tracker(self, url, bugid):
        try:
            match = re.match(r'[^\s/]+/(?P<project>[^\s/]+/[^\s/]+(/[^\s/]+)*?)/(-/)?(issues|merge_requests|commits?)', url)
            desc  = match.group(0)
            url   = 'https://%s' % desc
            # Commits are inconsistent in main and single page URLs
            desc = re.sub(r'/commit$', r'/commits', desc)
            name = desc.lower()
            bugurl = "%s/%s" % (re.sub(r'(://[^\s/]+)/[^\s/]+(/[^\s/]+)+/(-/)?',
                        r'\g<1>/api/v4/projects/%s/' % match.group('project').replace('/', '%2F'), url), bugid)
            # Commits are inconsistent in web and API URLs
            bugurl = bugurl.replace('/commit/', '/commits/')
            # Commits need an extra bit on API URLs
            bugurl = bugurl.replace('/commits/', '/repository/commits/')
            bugjson = utils.web.getUrl(bugurl).decode('utf-8')
            bug = json.loads(bugjson)
            return GitLab(name, url, desc, 'gitlab')
        except:
            pass

    def get_bug(self, bugtype, bugid):
        match = re.match(r'[^\s:]+://[^\s/]+/(?P<project>[^\s/]+/[^\s/]+(/[^\s/]+)*?)/(-/)?(issues|merge_requests|commits?)', self.url)
        url = "%s/%s" % (re.sub(r'(://[^\s/]+)/[^\s/]+(/[^\s/]+)+/(-/)?',
                 r'\g<1>/api/v4/projects/%s/' % match.group('project').replace('/', '%2F'), self.url), bugid)
        # Commits are inconsistent in web and API URLs
        url = url.replace('/commit/', '/commits/')
        if bugtype in ('issue', 'bug'):
            url = url.replace('/merge_requests/', '/issues/')
            url = url.replace('/commits/', '/issues/')
        elif bugtype in ('merge', 'mr', 'pull', 'pr'):
            url = url.replace('/issues/', '/merge_requests/')
            url = url.replace('/commits/', '/merge_requests/')
        elif bugtype == 'commit':
            url = url.replace('/issues/', '/commits/')
            url = url.replace('/merge_requests/', '/commits/')
        # Commits need an extra bit on API URLs
        url = url.replace('/commits/', '/repository/commits/')
        try:
            bugjson = utils.web.getUrl(url).decode('utf-8')
            bug = json.loads(bugjson)
        except Exception as e:
            raise BugtrackerError(self.errget % (self.description, e, url))
        try:
            product = match.group('project')
            if '/commits/' not in url:
                title = bug['title']
                status = bug['state']
                if bug['assignees']:
                    assino = len(bug['assignees'])
                    if assino == 1:
                        assignee = bug['assignees'][0]['name']
                    else:
                        assignee = '%d people' % assino
                else:
                    assignee = ''
            else:
                bugid = bug['id'][:7]
                title = bug['message'].split('\n', 1)[0]
                status = ''
                assignee = ''
            return (bugid, product, title, '', status, assignee, bug['web_url'], [], [])
        except Exception as e:
            raise BugtrackerError(self.errparse % (self.description, e, url))

class Gitea(IBugtracker):
    def get_tracker(self, url, bugid):
        try:
            match = re.match(r'[^\s/]+/[^\s/]+/[^\s/]+/(issues|pulls|commits?)', url)
            desc  = match.group(0)
            url   = 'https://%s' % desc
            # Commits are inconsistent in main and single page URLs
            desc = re.sub(r'/commit$', r'/commits', desc)
            name = desc.lower()
            bugurl = '%s/%s' % (re.sub(r'(://[^\s/]+)/', r'\g<1>/api/v1/repos/', url), bugid)
            # Commits are inconsistent in web and API URLs
            bugurl = bugurl.replace('/commit/', '/commits/')
            # Commits need an extra bit on API URLs
            bugurl = bugurl.replace('/commits/', '/git/commits/')
            bugjson = utils.web.getUrl(bugurl).decode('utf-8')
            bug = json.loads(bugjson)
            return Gitea(name, url, desc, 'gitea')
        except:
            pass

    def get_bug(self, bugtype, bugid):
        url = "%s/%s" % (re.sub(r'(://[^\s/]+)/', r'\g<1>/api/v1/repos/', self.url), bugid)
        # Commits are inconsistent in web and API URLs
        url = url.replace('/commit/', '/commits/')
        if bugtype in ('issue', 'bug'):
            url = url.replace('/pulls/', '/issues/')
            url = url.replace('/commits/', '/issues/')
        elif bugtype in ('pull', 'pr', 'merge', 'mr'):
            url = url.replace('/issues/', '/pulls/')
            url = url.replace('/commits/', '/pulls/')
        elif bugtype == 'commit':
            url = url.replace('/issues/', '/commits/')
            url = url.replace('/pulls/', '/commits/')
        # Commits need an extra bit on API URLs
        url = url.replace('/commits/', '/git/commits/')
        try:
            bugjson = utils.web.getUrl(url).decode('utf-8')
            bug = json.loads(bugjson)
        except Exception as e:
            raise BugtrackerError(self.errget % (self.description, e, url))
        try:
            product = '/'.join(self.url.split('/')[-3:-1])
            if '/commits/' not in url:
                title = bug['title']
                if 'merged' in bug and bug['merged']:
                    status = 'Merged'
                else:
                    status = bug['state']
                if bug['assignee']:
                    assignee = bug['assignee']['username']
                else:
                    assignee = ''
            else:
                bugid = bug['sha'][:7]
                title = bug['commit']['message'].split('\n', 1)[0]
                status = ''
                assignee = ''
            # Issues have no 'html_url', but pulls and commits do
            if 'html_url' in bug:
                htmlurl = bug['html_url']
            else:
                htmlurl = url.replace('/api/v1/repos/', '/')
            return (bugid, product, title, '', status, assignee, htmlurl, [], [])
        except Exception as e:
            raise BugtrackerError(self.errparse % (self.description, e, url))

cgitre = re.compile(r"""<a href='[^\s']+'>index</a> : <a .*?href='[^\s']+'>(?P<repo>[^\s<]+)</a>.*?
<tr><th>commit</th><td .*?class='(sha1|oid)'><a href='[^\s']+'>(?P<hash>[a-f0-9]+)</a>.*?
<div class='commit-subject'>(?P<subj>.*?)</div>""", re.I | re.DOTALL)
class CGit(IBugtracker):
    def get_tracker(self, url, bugid):
        try:
            match = re.match(r'(?P<url>(?P<desc>[^\s/]+\S*)/commit)/[^\s?]*\?([^\s?&]+&)?id=', url)
            desc  = match.group('desc')
            name  = desc.lower()
            url   = 'https://%s' % match.group('url')
            return CGit(name, url, desc, 'cgit')
        except:
            pass

    def get_bug(self, bugtype, bugid):
        url = "%s/?id=%s" % (self.url, bugid)
        try:
            bugdata = utils.web.getUrl(url).decode('utf-8')
        except Exception as e:
            if re.match(r'HTTP Error (404|400)', str(e)):
                raise BugNotFoundError
            raise BugtrackerError(self.errget % (self.description, e, url))
        match = cgitre.search(bugdata)
        if match:
            bugid = match.group('hash')[:7]
            title = utils.web.htmlToText(match.group('subj'), tagReplace=' ')
            title = re.sub(r'\s+', ' ', title)
            product = match.group('repo')
            return (bugid, product, title, '', '', '', url, [], [])
        else:
            raise BugtrackerError(self.errparseno % (self.description, url))

class Mantis(IBugtracker):
    def __init__(self, *args, **kwargs):
        IBugtracker.__init__(self, *args, **kwargs)
        self.soap_client = SoapClient("%s/api/soap/mantisconnect.php" % self.url, namespace="http://futureware.biz/mantisconnect")

    def get_tracker(self, url):
        try:
            match = re.match(r'(?P<url>(?P<desc>[^\s/]+)\S*)/view\.php', url)
            desc  = match.group('desc')
            name  = desc.lower()
            url   = 'https://%s' % match.group('url')
            return Mantis(name, url, desc, 'mantis')
        except:
            pass

    def get_bug(self, bugtype, bugid):
        url = "%s/api/rest/issues/%s" % (self.url, bugid)
        try:
            bugjson = utils.web.getUrl(url).decode('utf-8')
            bug = json.loads(bugjson)['issues'][0]
        except Exception as e:
            # REST API may not be enabled yet
            if 'HTTP Error 404' in str(e):
                return self.get_bug_old(bugtype, bugid)
            raise BugtrackerError(self.errget % (self.description, e, url))
        try:
            return (bugid, bug['project']['name'], bug['summary'], bug['severity']['name'], bug['resolution']['name'], '',
                    "%s/view.php?id=%s" % (self.url, bugid), [], [])
        except Exception as e:
            raise BugtrackerError(self.errparse % (self.description, e, url))

    def get_bug_old(self, bugtype, bugid): # Deprecated
        url = "%s/view.php?id=%s" % (self.url, bugid)
        try:
            raw = self.soap_client.mc_issue_get(username='', password='', issue_id=bugid)
        except Exception as e:
            if 'Issue #%s not found' % bugid in str(e):
                raise BugNotFoundError
            # Often SOAP is not enabled
            if '.' in self.name:
                supylog.exception(self.errget % (self.description, e, url))
                return
            raise BugtrackerError(self.errget % (self.description, e, url))
        if not hasattr(raw, 'id'):
            raise BugNotFoundError
        try:
            title = str(raw.summary)
            if checkBase64(title):
                title = decodeBase64(title)
            return (bugid, str(raw.project.name), title, str(raw.severity.name), str(raw.resolution.name), '', url, [], [])
        except Exception as e:
            raise BugtrackerError(self.errparse % (self.description, e, url))

# For Trac-based trackers we get the tab-separated-values format.
# The other option is a comma-separated-values format, but if the description
# has commas, things get tricky.
# This should be more robust than the screen scraping done previously.
class Trac(IBugtracker):
    def get_tracker(self, url):
        try:
            match = re.match(r'(?P<desc>[^\s/]+)\S*/ticket', url)
            desc  = match.group('desc')
            name  = desc.lower()
            url   = 'https://%s' % match.group(0)
            return Trac(name, url, desc, 'trac')
        except:
            pass

    def get_bug(self, bugtype, bugid): # This is still a little rough, but it works :)
        url = "%s/%s?format=tab" % (self.url, bugid)
        try:
            raw = utils.web.getUrl(url).decode('utf-8')
        except Exception as e:
            # Due to unreliable matching
            if '.' in self.name:
                supylog.exception(self.errget % (self.description, e, url))
                return
            if 'HTTP Error 500' in str(e):
                raise BugNotFoundError
            raise BugtrackerError(self.errget % (self.description, e, url))
        try:
            raw = raw.replace('\r\n', '\n')
            (headers, rest) = raw.split('\n', 1)
            headers = headers.strip().split('\t')
            rest = rest.strip().split('\t')

            title = rest[headers.index("summary")]
            status = rest[headers.index("status")]
            package = rest[headers.index("component")]
            severity = assignee = ""
            if "severity" in headers:
                severity = rest[headers.index("severity")]
            elif "priority" in headers:
                severity = rest[headers.index("priority")]
            if "owner" in headers:
                assignee = rest[headers.index("owner")]
            return (bugid, package, title, severity, status, assignee, "%s/%s" % (self.url, bugid), [], [])
        except Exception as e:
            # Due to unreliable matching
            if '.' in self.name:
                supylog.exception(self.errparse % (self.description, e, url))
                return
            raise BugtrackerError(self.errparse % (self.description, e, url))

# Introspection is quite cool
defined_bugtrackers = {}
v = vars()
for k in list(v.keys()):
    if type(v[k]) == type(IBugtracker) and issubclass(v[k], IBugtracker) and not (v[k] == IBugtracker):
        defined_bugtrackers[k.lower()] = v[k]
