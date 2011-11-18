"""
See the FreeAgent API docs::

  http://www.freeagent.com/developers/freeagent-api

Unlike Harvest, FreeAgent API v1 only supports XML, no JSON.

GET bank account list with::

  curl -u user@company.com:PASSWORD
       -H 'Accept: application/xml' -H 'Content-Type: application/xml'
       https://company.freeagent.com/bank_accounts

POST transaction to bank id::

  curl -v
          -u user@company.com:PASSWORD
           -H 'Accept: application/xml'
           -H 'Content-Type: application/xml'
           --data @bankacctentry.xml
           https://company.freeagent.com/bank_accounts/ACCTNUM/bank_account_entries

Is there really no way to restrict date range on these?
* /projects/PROJECT_ID/invoices
* /projects/PROJECT_ID/timeslips

Example using upcoming v2 API and JSON format output. At this time,
the API has a dummy company so the company and username are not used
by FreeAgent server. Per FreeAgent's request, I'm hiding the actual
URL and our OAuth token here::

  >>>fa = freeagent.FreeAgent('COMPANY', 'USER@DOMAIN', 'OAuthBearerToken', dataformat='json', api="v2", fac_url="DONT_SHOW_V2_HERE_YET)
  INFO:root:__init__ headers={'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Bearer OAuthBearerToken', 'User-Agent': 'https://github.com/shentonfreude/FreeAgent'}

  >> resp = fa._get_response('/company')
  INFO:root:_get_response url=https://v2_fake_host.freeagent.com/v2/company
  >>> print resp.readlines()
  ['{"company":{"type":"UkLimitedCompany","currency":"GBP","mileage_units":"miles"}}']

  >>> resp = fa._get_response('/users')
  INFO:root:_get_response url=https://v2_fake_host.freeagent.com/v2//users
  >>> resp.readlines()
  ['{"users":[{"path":"/v2/users/112","first_name":"Chris","last_name":"Shenton","email":"chris@koansys.com","role":"Director","permission_level":8,"opening_mileage":0,"updated_at":"2011-11-18T10:20:27Z","created_at":"2011-11-18T10:20:27Z"}]}']

Resources:
* /company
* /invoices
* /users    [/:id] [/me]
* /timeslips [:id]
* /tasks     [:id] [?project=:project]  !!!!
* /projects  [:id]
* /contacts  [:id]
...

Paging:
* GET /v2/RESOURCE?page=5&per_page=50]; see returned 'Link' header (prev,next,first,last)

To get started, I need to:
1. create a contact
2. create a project with that contact
3. create a task with that project
4. create a timeslip with that task

I should create Class-level RESTful CRUD methods: get (one, multiple),
create, update, delete. They'd use GET, POST, PUT, DELETE.
Resource-type-specific methods would require mandatory parameters and
allow option ones.
"""

import datetime
from base64 import encodestring
import xml.etree.cElementTree as et
import logging
import urllib2

logging.basicConfig(level=logging.DEBUG)

class FreeAgentError(Exception): pass
class BadResponseFormatError(FreeAgentError): pass
class NonXMLResponseError(FreeAgentError): pass
class BadAuthError(FreeAgentError): pass
class BadResponse(FreeAgentError): pass

class FreeAgent(object):
    """FreeAgentCental connection and methods.

    domain: companyname
    email:  user@companyname.com
    password: SqueamishOssifrage
    """
    def __init__(self, domain, email, password,
                 dataformat="xml", authformat="basic", api="v1",
                 fac_url="https://%s.freeagent.com"):
        if dataformat not in ("xml", "json"):
            raise FreeAgentError("format must be xml or json")
        if authformat not in ("basic", "oauth"):
            raise FreeAgentError("authformat must be basic or oauth")
        if api not in ("v1", "v2"):
            raise FreeAgentError("api must be v1 or v2")
        self.domain = domain
        self.email = email
        self.password = password
        self.dataformat = dataformat
        if api == "v1":
            self.fac_url = fac_url % self.domain
            self.authorization = "Basic %s" % encodestring('%s:%s' % (self.email, self.password))[:-1]
        else:
            self.fac_url = fac_url # must pass this in, don't show in GitHub yet
            self.authorization = "Bearer %s" % password
        self.headers = {
            'Authorization': self.authorization,
            'Accept': 'application/%s' % dataformat,
            'Content-Type': 'application/%s' % dataformat,
            'User-Agent': 'https://github.com/shentonfreude/FreeAgent'
            }
        logging.info("__init__ headers=%s" % self.headers)

    def _get_response(self, path, data=None):
        """Take auth creds, REST path, POST data, return HTTP response file hanele.
        If there's data, then urllib2 makes this a POST as needed.
        Response is XML, no JSON available (yet).
        """
        url = self.fac_url + path
        logging.info("_get_response url=%s" % url)
        request = urllib2.Request(url, data, self.headers)
        try:
            site = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            if e.getcode() == 401:
                raise BadAuthError, \
                    "Authentication failed, check username/password, " \
                    "ensure Settings->API is enabled (%s)" % e
            else:
                raise BadResponse, "Bad Response from FreeAgent: %s" % e
        if not site.headers['content-type'].startswith("application/%s" % self.dataformat):
            raise BadResponseFormatError, "Non XML/JSON response content-type='%s', check your domain" % (
                site.headers['content-type'],)
        return site

    # TODO: This is a dupe of _get_response almost, unify them.
    # Add knob to allow non-xml response on request-basis for e.g., application/pdf

    def _get_response_noheaders(self, path, data=None):
        """Take auth creds, REST path, return HTTP response file hanele.
        We use this for getting PDF of invoice.
        """
        url = self.fac_url + path
        logging.info("_get_response_noheaders url=%s" % url)
        auth_headers = {
            'Authorization': self.authorization,
            }
        request = urllib2.Request(url, data, auth_headers)
        try:
            site = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            raise BadResponse, "Bad Response from FreeAgent: %s" % e
        return site

    def _node_dict(self, node):
        """Return dict from XML node's children.
        Elements have tag, optional attributes, and text.
        Return dict of tag and text.
        DANGER:
        * this ignores attributes so you're hosed if you depend on them
        * doesn't follow recursive structures
        """
        children = [(child.tag,child.text) for child in node.getchildren()]
        return dict(children)


    def _get_default_begin_end(self, begin, end):
        """Set a sane default date range if values aren't specified.
        """
        if not begin:
            begin = datetime.datetime.now().isoformat()[:5] + "01-01"
        if not end:
            end = datetime.datetime.now().isoformat()[:10]
        return begin, end

    def get_raw_node(self, urlpath, nodename):
        response = self._get_response(urlpath)
        root = et.parse(response).getroot()
        return root

    def get_keyed_node(self, urlpath, nodename, key='id'):
        """Return list of dicts of nodes by URLpath with chosen key.

        BUGBUG: this doesn't handle hierarchical data like invoices.
        """
        node = self.get_raw_node(urlpath, nodename)
        return dict([(n.find(key).text, self._node_dict(n)) for n in node.findall(nodename)])

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

    def get_contacts(self):
        """
        """
        return self.get_keyed_node("/contacts", "contact")

    def get_timeslips(self, begin=None, end=None):
        """
        Return timeslips for all users in specified date range.

        Begin and End default to specify "since the beginning of the year"
        or something reasonable, TBD.

        The authenticating user must have admin rights to read all users' slips.

        TODO: only want Billable time.

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
        begin, end = self._get_default_begin_end(begin, end)
        return self.get_keyed_node("/timeslips?view=%s_%s" % (begin, end), "timeslip")


    def get_invoices(self, begin=None, end=None, status="Paid"):
        """Return list of invoices with nested dict of invoice-items. NOT KEYED BY ID YET.
        """
        invoices = []
        begin, end = self._get_default_begin_end(begin, end)
        for invoice_node in self.get_raw_node("/invoices?view=%s_%s" % (begin, end), "invoice"):
            invdict = self._node_dict(invoice_node)
            items = invoice_node.find("invoice-items")
            invdict["invoice-items"] = [ self._node_dict(item) for item in items ]
            invoices.append(invdict)
        return invoices

