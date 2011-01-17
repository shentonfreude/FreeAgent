"""
 Get bank account list with::

   curl -u user@company.com:PASSWORD
        -H 'Accept: application/xml' -H 'Content-Type: application/xml'
        https://company.freeagentcentral.com/bank_accounts

 POST transaction to bank id::

   curl -v
           -u user@company.com:PASSWORD
            -H 'Accept: application/xml'
            -H 'Content-Type: application/xml'
            --data @bankacctentry.xml
            https://company.freeagentcentral.com/bank_accounts/ACCTNUM/bank_account_entries
"""

import csv
import datetime
from base64 import encodestring
import xml.etree.cElementTree as et
import logging
import sys
import urllib2

logging.basicConfig(level=logging.DEBUG)

class FreeAgentError(Exception): pass
class NonXMLResponseError(FreeAgentError): pass
class BadAuthError(FreeAgentError): pass
class BadResponse(FreeAgentError): pass

class FreeAgent(object):
    """FreeAgentCental connection and methods.
    """
    def __init__(self, domain, email, password):
        self.domain = domain
        self.email = email
        self.password = password
        self.fac_url = "https://%s.freeagentcentral.com/" % self.domain
        self.authorization = "Basic %s" % encodestring('%s:%s' % (self.email, self.password))[:-1]

    def _get_response(self, path, data=None):
        """Take auth creds, REST path, POST data, return HTTP response file hanele.
        If there's data, then urllib2 makes this a POST as needed.
        Response is XML, no JSON available (yet).
        """
        url = self.fac_url + path
        logging.info("_get_response url=%s" % url)
        print "# URL=%s" % url
        request = urllib2.Request(url, data,
                                  headers={'Accept' : 'application/xml',
                                           'Content-Type' : 'application/xml'},
                                  )
        request.add_header("Authorization", self.authorization)
        try:
            site = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            # XXX wrongly catches 404=NotFound, 400=BadRequest too
            raise BadAuthError, "Authentication failed, check your username and password, ensure Settings->API is enabled (%s)" % e
        if not site.headers['content-type'].startswith("application/xml"):
            raise NonXMLResponseError, "Not an XML response, check your domain"
        return site

    def _node_dict(self, node):
        """Return dict from XML node's children.
        Elements have tag, optional attributes, and text.
        Return dict of tag and text.
        DANGER: this ignores attributes so you're hosed if you depend on them.
        """
        children = [(child.tag,child.text) for child in node.getiterator()]
        return dict(children)

    def get_keyed_node(self, urlpath, nodename, key='id'):
        """Return list of dicts of nodes by URLpath with chosen key.
        """
        response = self._get_response(urlpath)
        root = et.parse(response).getroot()
        return dict([(n.find(key).text, self._node_dict(n)) for n in root.findall(nodename)])

    def get_projects(self, begin=None, end=None):
        """
        Get ALL project (including non-active).

        We have to ask for view=all to get non-active projects which
        may have been charged earlier but no longer used.

        CONTACT may be empty :-( 

        <project>
          <id type="integer">25922</id>
          <contact-id type="integer">43868</contact-id>
          <name>Wordpress-to-Plone</name>
          <currency>USD</currency>
          <status>Active</status>
          <starts-on type="date"></starts-on>
          <ends-on type="date"></ends-on>
          <billing-basis type="decimal">8.0</billing-basis>
          <hours-per-day type="decimal">8.0</hours-per-day>
          <billing-period>hour</billing-period>
          <normal-billing-rate>125.0</normal-billing-rate>
          <budget type="integer">0</budget>
          <budget-units>Hours</budget-units>
          <uses-project-invoice-sequence type="boolean">false</uses-project-invoice-sequence>
          <contacts-po-reference></contacts-po-reference>
          <is-ir35 type="boolean"></is-ir35>
          <notes-count type="integer">0</notes-count>
          <basecamp-id type="integer"></basecamp-id>
          <created-at type="datetime">2010-01-02T23:14:35Z</created-at>
          <updated-at type="datetime">2010-01-02T23:15:44Z</updated-at>
        </project>
        """
        return self.get_keyed_node("/projects?view=all", "project")

    def get_tasks(self):
        """
        CONTACT may be empty :-(
        We can ask for ?view={all,active,copmleted,cancelled,inactive}
        But generically we want all so we can deref timeslips

        <task>
          <billing-period>hour</billing-period>
          <billing-rate type="decimal">125.0</billing-rate>
          <id type="integer">20909</id>
          <is-billable type="boolean">true</is-billable>
          <name>Some users offline (fireqall over limit)</name>
          <project-id type="integer">25922</project-id>
          <status>Active</status>
        </task>
        """
        return self.get_keyed_node("/tasks", "task")

    def get_users(self):
        """
        """
        return self.get_keyed_node("/company/users", "user")

    def get_timeslips(self, begin=None, end=None):
        """
        <timeslip>
          <id type="integer">5766839</id>
          <dated-on type="datetime">2011-01-13T00:00:00+00:00</dated-on>
          <hours type="decimal">4.5</hours>
          <comment>finish setup, ssl redirecion, apache, postfix, buildout, logo</comment>
          <user-id type="integer">7263</user-id>
          <project-id type="integer">95867</project-id>
          <task-id type="integer">154479</task-id>
          <updated-at type="integer">Thu Jan 13 19:16:12 UTC 2011</updated-at>
          <status />
        </timeslip>
        """
        if not begin:
            begin = datetime.datetime.now().isoformat()[:5] + "01-01"
        if not end:
            end = datetime.datetime.now().isoformat()[:10]
        return self.get_keyed_node("/timeslips?view=%s_%s" % (begin, end), "timeslip")



if __name__ == "__main__":
    domain = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    fac = FreeAgent(domain, email, password)

    projs = fac.get_projects()
    tasks = fac.get_tasks()
    users = fac.get_users()
    timeslips = fac.get_timeslips("2010-01-01", "2010-12-31")
    #timeslips = fac.get_timeslips()


    fields = ['date', 'project', 'task', 'user', 'status', 'hours', 'comment']
    dw = csv.DictWriter(sys.stdout, fields )
    dw.writeheader()            # python2.7 only

    proj_user_hours = {}

    for t in timeslips.values():
        proj = projs[t['project-id']]['name']
        task = tasks[t['task-id']]['name']
        user = user = users[t['user-id']]['email']
        d = dict(zip(fields,
                     (t['dated-on'][:10],
                      proj,
                      task,
                      user,
                      t['status'],
                      t['hours'],
                      t['comment'])))
        dw.writerow(d)

        if not proj in proj_user_hours:
            proj_user_hours[proj] = {}
        if not user in proj_user_hours[proj]:
            proj_user_hours[proj][user] = 0
        proj_user_hours[proj][user] += float(t['hours'])

from pprint import pprint as pp
pp(proj_user_hours)
