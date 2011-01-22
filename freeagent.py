"""
See the FreeAgent API docs::

  http://www.freeagentcentral.com/developers/freeagent-api

Unlike Harvest, FreeAgent only supports XML, no JSON.

GET bank account list with::

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

Is there really no way to restrict date range on these?
* /projects/PROJECT_ID/invoices
* /projects/PROJECT_ID/timeslips
"""

import datetime
from base64 import encodestring
import xml.etree.cElementTree as et
import logging
import urllib2

logging.basicConfig(level=logging.DEBUG)

class FreeAgentError(Exception): pass
class NonXMLResponseError(FreeAgentError): pass
class BadAuthError(FreeAgentError): pass
class BadResponse(FreeAgentError): pass

class FreeAgent(object):
    """FreeAgentCental connection and methods.

    domain: companyname.freeagent.com
    email:  user@companyname.com
    password: SqueamishOssifrage
    """
    def __init__(self, domain, email, password):
        self.domain = domain
        self.email = email
        self.password = password
        self.fac_url = "https://%s.freeagentcentral.com/" % self.domain
        self.authorization = "Basic %s" % encodestring('%s:%s' % (self.email, self.password))[:-1]
        self.headers = {
            'Authorization': self.authorization,
            'Accept': 'application/xml',
            'Content-Type': 'application/xml',
            'User-Agent': 'freeagent.py'
            }

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
            # XXX wrongly catches 404=NotFound, 400=BadRequest too
            raise BadAuthError, "Authentication failed, check your username and password, ensure Settings->API is enabled (%s)" % e
        if not site.headers['content-type'].startswith("application/xml"):
            raise NonXMLResponseError, "Not an XML response, check your domain"
        return site

    def xmldict(self, node):
        """Return a recursive dict and list of dicts represeting the XML.

        If a node has no children a dict of the tag and text is returned.
        If it has children, return a dict with the tag and list of recursed children.

        <flintstones>
          <kids>
            <kid>pebbles</kid>
            <kid>bambam</kid>
          </kids>
          <car>Courtesy of Fred's two feet</car>
        </flintstones>

        Results in:

        {'flintstones': [{'kids': [{'kid': 'pebbles'},
                                   {'kid': 'bambam'}]},
                         {'car': "Courtesy of Fred's two feet"}]}


        BUGBUG: shape is not quite right:

            pp(invoice)
            [{'id': '545203'},
             {'status': 'Paid'},
             {'invoice-items': [{'invoice-item': [{'id': '903031'},
                                                  {'description': 'www1 replacement server on 13 Sep 10'},
        Should be more like:
            {id:xxx, status:xxx, invoice-items: [ {...} {...}]                                                   
                         
        """
        if len(node) == 0:
            return {node.tag : node.text}
        return { node.tag : [ self.xmldict(child) for child in node ]}

    def _node_dict(self, node):
        """Return dict from XML node's children.
        Elements have tag, optional attributes, and text.
        Return dict of tag and text.
        DANGER: this ignores attributes so you're hosed if you depend on them.
        """
        children = [(child.tag,child.text) for child in node.getiterator()]
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

        BUGBUG: this doesn't handle hierarchical data!  For example:

        <invoices type="array">
          <invoice>
            <id type="integer">100183</id>
            <net-value type="decimal">24982.4</net-value>
            <invoice-items type="array">
              <invoice-item>
                <item-type>Hours</item-type>
                <price type="decimal">152.0</price>
              </invoice-item>
              <invoice-item>
                <item-type>Services</item-type>
                <price type="decimal">24982.4</price>
              </invoice-item>
            </invoice-items>
          </invoice>
        </invoices>

        We have {'invoice-items': ''} and lose the individual 'invoice-item' elements.
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

    def get_invoices_XXX(self, begin=None, end=None, status="Paid"):
        """Return invoices in given duration with given status, default=Paid.

        For understanding a worker's profit, We want to tally cost,
        but exclude billed-back items.  The invoice-item item-type is
        one of:
        * Hours
        * Days
        * Months
        * Years
        * Products
        * Services
        * Expenses
        * Discount
        * Credit
        * Comment



        <invoices type="array">
          <invoice>
            <id type="integer">100183</id>
            <company-id type="integer">5194</company-id>
            <project-id type="integer">25190</project-id>
            <contact-id type="integer">42386</contact-id>
            <dated-on type="datetime">2009-01-01T00:00:00Z</dated-on>
            <due-on type="datetime">2009-01-31T00:00:00Z</due-on>
            <reference>2008-12</reference>
            <currency>USD</currency>
            <exchange-rate>1.0</exchange-rate>
            <net-value type="decimal">24982.4</net-value>
            <sales-tax-value type="decimal">0.0</sales-tax-value>
            <second-sales-tax-value type="decimal">0.0</second-sales-tax-value>
            <status>Paid</status>
            <comments>OLD DATA</comments>
            <discount-percent type="decimal"></discount-percent>
            <po-reference></po-reference>
            <omit-header type="boolean">false</omit-header>
            <payment-terms-in-days type="integer">30</payment-terms-in-days>
            <written-off-date type="datetime"></written-off-date>
            <ec-status></ec-status>
            <invoice-items type="array">
              <invoice-item>
                <id type="integer">224835</id>
                <description>HITSS</description>
                <project-id type="integer" nil="true"></project-id>
                <invoice-id type="integer">100183</invoice-id>
                <item-type>Hours</item-type>
                <price type="decimal">152.0</price>
                <quantity type="decimal">0.0</quantity>
                <sales-tax-rate type="decimal">0.0</sales-tax-rate>
                <second-sales-tax-rate type="decimal">0.0</second-sales-tax-rate>
                <nominal-code>001</nominal-code>
              </invoice-item>
              ...
        """
        begin, end = self._get_default_begin_end(begin, end)
        invoices = self.get_keyed_node("/invoices?view=%s_%s" % (begin, end), "invoice")
        #import pdb;pdb.set_trace()
        # This gets the invoice, but not the entries, which have the hours/services/expense
        #return dict([(k,v) for k,v in invoices.items() if v['status']==status])
        # Return raw node for xmldict processing
        return invoices

    def get_invoices(self, begin=None, end=None, status="Paid"):
        """Return eTree of invoices in given duration with given status, default=Paid.
        """
        begin, end = self._get_default_begin_end(begin, end)
        invoices = self.get_raw_node("/invoices?view=%s_%s" % (begin, end), "invoice")
        return invoices

