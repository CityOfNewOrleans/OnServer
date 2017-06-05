infname = 'onserver_output.txt'
outfname = 'remake_services.txt'

services = []

print 'Scanning OnServer Output...'
with open(infname, 'r') as f:
    servicerow = None
    lastrow = None
    for row in f:
        if set([x for x in row.strip()]) == set('-'):
            #This is the spacer row.  The previous row is the MapService path,
            # and the next row contains the MXD path and name.
            servicerow = lastrow[:]
            lastrow = '###'
        elif lastrow == '###' and servicerow != None:
            #We've stumbled across the MXD (ideally)
            services.append({'svcrow': servicerow, 'mxd': row.strip()})
            lastrow = row.strip()
            servicerow = None
        else:
            lastrow = row.strip()
print ' - {0} MapServices found.'.format(len(services))

print 'Writing Service Creation List...'
untitleds = []
count = 0
with open(outfname, 'w') as g:
    for svc in services:
        url = svc['svcrow'].split('(')[-1][:-1]
        if svc['mxd'] == 'Untitled':
            untitleds.append(svc['svcrow'])
        else:
            g.write('"{0}" "{1}"\n'.format(svc['mxd'], url))
            count += 1
print ' - {0} creation command parameters written.'.format(count)
if len(untitleds) > 0:
    print ' - {0} services created from unsaved MXDs.'.format(len(untitleds))
    print ' - uncreatable services are:'
    print '   + ' + '\n   + '.join(sorted(untitleds))

print 'Complete.'