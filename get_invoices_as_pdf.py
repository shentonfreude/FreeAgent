# Bank wants copies of all invoices going back 2 years.
# I can get the XML for all with:
# curl -u MYEMAIL:MYPASSWORD!' \
#      -H 'Accept: application/xml' \
#      -H 'Content-Type: application/xml' \
#      https://MYCOMPANY.freeagentcentral.com/invoices
# and if I have the invoice ID I can ask for a PDF with:
# https://koansys.freeagentcentral.com/invoices/1924153.pdf
#
# Use like:
# python get_invoices_as_pdf.py MYFACSUBDOMAIN MYEMAIL 'MYPASSWORD''
###############################################################################

import logging
import sys

import freeagent

domain = sys.argv[1]
email = sys.argv[2]
password = sys.argv[3]

logging.basicConfig(level=logging.DEBUG)

fa = freeagent.FreeAgent(domain, email, password)

#invoices = fa.get_invoices(begin='2009-08-01', end='2011-09-01')
invoices = fa.get_invoices(begin='2011-08-01', end='2011-09-01')

for invoice in invoices:
    date = invoice['dated-on'][:10]
    fac_id = invoice['id']
    our_id = invoice['reference']
    print 'invoice id=%s our_id#%s date=%s' % (fac_id, our_id, date)
    outname = "invoice_%s_%s_%s.pdf" % (date, our_id, fac_id)
    #pdf_fh = fa._get_response_noheaders('invoices/%s.pdf' % fac_id)
    pdf_fh = fa._get_response_noheaders('invoices/%s.pdf' % fac_id)
    out = open(outname, 'wb')
    out.write(pdf_fh.read())
    out.close()



