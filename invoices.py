# BUGBUG: doesn't get the invoice *items* since my XML-Dict thing isn't recursion-aware (yet).

import sys
from pprint import pprint as pp
from freeagent import FreeAgent
#             # mycompany, myuser@mycompany.com, mypassword
fa = FreeAgent(sys.argv[1], sys.argv[2], sys.argv[3])
invs = fa.get_invoices("2010-10-01", "2011-01-31")
pp(invs)            # stupid nonclassful use

invoices_tree = fa.xmldict(invs)
for invoice_dict in invoices_tree['invoices']:
    invoice = invoice_dict['invoice']
    import pdb;pdb.set_trace()
    print invoice['dated-on'], invoice['status'], invoice['net-value']
