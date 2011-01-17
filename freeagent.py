"""
 Get bank account list with:
 curl -u user@company.com:PASSWORD
      -H 'Accept: application/xml' -H 'Content-Type: application/xml'
      https://company.freeagentcentral.com/bank_accounts

 POST transaction to bank id:

 curl -v
         -u user@company.com:PASSWORD
	  -H 'Accept: application/xml'
	  -H 'Content-Type: application/xml'
	  --data @bankacctentry.xml
	  https://company.freeagentcentral.com/bank_accounts/ACCTNUM/bank_account_entries
"""

import sys
#from webob.exc import HTTPFound
import urllib2
from base64 import encodestring, decodestring
import xml.etree.cElementTree as et
import logging
import datetime
import json

logging.basicConfig(level=logging.DEBUG)

class FareError(Exception): pass
class NonXMLResponseError(FareError): pass
class BadAuthError(FareError): pass
class BadResponse(FareError): pass

class FreeAgentCentral(object):
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

    def get_projects(self, begin=None, end=None):
        """
        CONTACT may be empty :-(
        We can ask for ?view={all,active,copmleted,cancelled,inactive}
        But generically we want all so we can deref timeslips

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
        response = self._get_response("/projects")
        root = et.parse(response).getroot()
        projs = {}
        for p in root.findall('project'):
            projs[p.find('id').text] = p.find('name').text
        return projs

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
        response = self._get_response("/tasks")
        root = et.parse(response).getroot()
        objs = {}
        for i in root.findall('task'):
            objs[i.find('id').text] = i.find('name').text
        return objs

    def get_users(self):
        """
        """
        response = self._get_response("/company/users")
        root = et.parse(response).getroot()
        objs = {}
        for i in root.findall('user'):
            objs[i.find('id').text] = i.find('email').text # first-name, last-name, ...
        return objs



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
        response = self._get_response("/timeslips?view=%s_%s" % (begin, end))
        return response


if __name__ == "__main__":
    domain = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    fac = FreeAgentCentral(domain, email, password)

    projs = fac.get_projects()
    print "PROJS", projs

    tasks = fac.get_tasks()
    print "TASKS", tasks

    users = fac.get_users()
    print "USERS", users

    timesheets = fac.get_timeslips()
    #from pprint import pprint as pp
    #pp(  timesheets.readlines())

    tree = et.parse(timesheets)
    root = tree.getroot()
    print "root:", et.tostring(root)
    timeslips = root.findall('timeslip')
    for ts in timeslips:
        timeslip = {}
        timeslip['id'] = ts.find('id').text
        timeslip['date'] = ts.find('dated-on').text
        timeslip['hours'] = ts.find('hours').text # can it be non-decimal??
        timeslip['user-id'] = ts.find('user-id').text
        timeslip['task-id'] = ts.find('task-id').text
        timeslip['project-id'] = ts.find('project-id').text
        timeslip['updated-at'] = ts.find('updated-at').text
        #print "date", ts.find('dated-on').text[:10]
        print timeslip
