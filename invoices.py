# BUGBUG: doesn't get the invoice *items* since my XML-Dict thing isn't recursion-aware (yet).

import sys
import csv
import logging
from pprint import pprint as pp
from freeagent import FreeAgent

logging.basicConfig(level=logging.DEBUG)

#             # mycompany, myuser@mycompany.com, mypassword
fa = FreeAgent(sys.argv[1], sys.argv[2], sys.argv[3])

projs = fa.get_projects()
conts = fa.get_contacts()
invs  = fa.get_invoices("2010-01-01", "2010-12-31")

fields = ['inv#', 'date',
          'contact', 'proj',
          'status', 'invoice$',
          'item$', 'type', 'qty', 'desc']

dw = csv.DictWriter(sys.stdout, fields)
dw.writeheader()            # python2.7 only

proj_netval = {} # Includes Expenses
proj_income = {} # Exclude Expenses, but how to accommodate markup profit?

# TODO: Exclude Un-Paid items

for inv in invs:
    proj = projs[inv['project-id']]['name']
    cont = conts[inv['contact-id']]['organisation-name']
    net_value = float(inv['net-value'])
    status = inv['status']
    if status == "Paid":
        proj_netval[proj] = proj_netval.get(proj, 0) + net_value
        proj_income[proj] = proj_income.get(proj, 0) + net_value

    for item in inv['invoice-items']:
        if status == "Paid" and item['item-type'] == "Expenses":
            proj_income[proj] -= float(item['price'])
        d = dict(zip(fields,
                     (inv['reference'], inv['dated-on'][:10],
                      cont, proj,
                      status, net_value,
                      item['price'], item['item-type'], item['quantity'], item['description'])))
        dw.writerow(d)

for p in sorted(proj_income):
    logging.info("%-24s %10.2f (%10.2f with expenses)" % (p, proj_income[p], proj_netval[p]))



