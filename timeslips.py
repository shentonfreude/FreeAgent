import sys
import csv
from freeagent import FreeAgent

domain = sys.argv[1]
email = sys.argv[2]
password = sys.argv[3]
fac = FreeAgent(domain, email, password)

projs = fa.get_projects()
tasks = fa.get_tasks()
users = fa.get_users()
timeslips = fa.get_timeslips("2011-01-01", "2011-12-31")
#timeslips = fa.get_timeslips()


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
