# BUGBUG: doesn't get the invoice *items* since my XML-Dict thing isn't recursion-aware (yet).
from pprint import pprint as pp
from freeagent import FreeAgent
fa = FreeAgent("koansys","chris@koansys.com","K04nsys")
invs = fa.get_invoices()
pp(invs)

