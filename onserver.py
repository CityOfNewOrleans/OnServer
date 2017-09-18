import argparse
import datetime
import errno
import json
import string
import os
import sys

from ctypes import windll

################################################################################
#                                                                              #
#  OnServer.py - search for a featureclass, database, mxd, or service,         #
#                and view info about the services that contain that item.      #
#                                                                              #
#  r1: JBRIII - 9/15/15 - Inital release.                                      #
#  r2: JBRIII - 9/16/15 - Add config folder search, eliminating settings.      #
#  r3: JBRIII - 9/24/15 - Add better parsing of db name for sde.               #
#  r4: JBRIII - 9/29/15 - Added veryquiet output.                              #
#  r5: JBRIII - 10/1/15 - Changed output delimiter.                            #
#                                                                              #
################################################################################

class MapService(object):
    """
    Object containing info about a map service.
    """
    def __init__(self, mxd, servicename, url, datasources):
        """
        Initialize the class.

        mxd is the name of the map document that created the service
        servicename is the name of the map service
        url is the relative URL of the map service
        datasources is a dict: {'db1': [fc1, fc2, ...], ...}

        no return.
        """
        self.name = servicename
        self.url = url
        self.mxd = mxd
        self._dbnames = sorted(datasources.keys())
        self._featureclasses = [y for x in datasources.values() for y in x]
        self._datastructure = datasources

    def uses_feature(self, fcname):
        """
        Tests (by name only) to see if a map service uses a featureclass.

        fcname is the name of the featureclass

        returns True if the featureclass is used by the map, False otherwise.
        """
        used = False
        if any([fcname.upper() in y for y in [x.upper() for x in self._featureclasses]]):
            used = True
        return used

    def uses_database(self, dbname):
        """
        Tests (by name only) to see if a map service uses a database (gdb, folder, etc.).

        dbname is the name of the database

        returns True if the database is used by the map, False otherwise.
        """
        used = False
        if any([dbname.upper() in y for y in [x.upper() for x in self._dbnames]]):
            used = True
        return used
    
    def quiet_repr(self):
        """
        Create a 'quiet' representation of the map service

        returns a string for printing
        """
        output = '{0} ({1})'.format(self.name, self.url)
        return output

    def veryquiet_repr(self):
        """
        Create a 'very quiet' representation of the map service

        returns a string for printing
        """
        output = '{0}'.format(self.url)
        return output

    def __repr__(self):
        """
        Creates a printable representation of the map service.

        returns a string for printing.
        """
        dbline = ' - {0}'
        fcline = '   + {0}'
        output = ['{0} ({1})'.format(self.name, self.url)]
        output.append('-' * len(output[0]))
        output.append(' {0}'.format(self.mxd))
        for db in self._dbnames:
            output.append(dbline.format(db))
            for fc in sorted(self._datastructure[db]):
                output.append(fcline.format(fc))
            output.append('')
        output.append('')
        return '\n'.join(output)

    def csv_repr(self):
        """
        Create a printable CSV representation of the map service.

        returns a string for printing.
        """
        if len(self._dbnames) > 1:
            output = '{0},{1},{2},{3}'.format(self.name, self.url, self.mxd, self._dbnames[0])
            for db in self._dbnames[1:]:
                dbnames_output = '\n,,,{0}'.format(db)
                output = output + dbnames_output
        else:
            output = '{0},{1},{2},{3}'.format(self.name, self.url, self.mxd, self._dbnames[0])
        return output

    def md_repr(self):
        """
        Creates a printable Markdown representation of the map service.

        returns a string for printing.
        """
        dbline = '- {0}'
        fcline = '    + {0}'
        output = ['## {0} ({1})\n'.format(self.name, self.url)]
        output.append('**{0}**\n'.format(self.mxd.replace("\\", "\\\\")))
        for db in self._dbnames:
            output.append(dbline.format(db.replace("\\", "\\\\")))
            for fc in sorted(self._datastructure[db]):
                output.append(fcline.format(fc))
            output.append('')
        output.append('')
        return '\n'.join(output)

def find_arcserver_config():
    """
    Scan the system drives (Windows) to find the ArcGIS Server Cofiguration.
    (cribbed from http://stackoverflow.com/a/827398)

    returns the path to the configuration folder.
    raises IOError if the configuration cannot be found.
    """
    arcdir = ''
    cfgfmt = '{0}:\\arcgisserver\\directories\\arcgissystem\\arcgisinput'
    #First, get a list of the available drives on the Windows machine.
    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    for letter in string.uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1

    #Now, look for the configuration directory
    for drv in drives:
        if os.path.exists(cfgfmt.format(drv)):
            arcdir = cfgfmt.format(drv)
            break
    else:
        #Raise the not found error if we don't find a suitable config path.
        raise IOError(errno.ENOENT, os.strerror(errno.ENOENT))
    return arcdir


def get_manifests(arcroot):
    """
    Walk the directories rooted at arcroot, and find the manifest.json files.
    
    arcroot is the directory containing the map service definitions
    
    returns a list of all manifest.json files.
    """
    manifests = []
    for root, dirs, files in os.walk(arcroot):
        if 'manifest.json' in files:
            manifests.append(os.path.join(root, 'manifest.json'))
            
    return manifests
    
def parse_manifest(manfile):
    """
    Read a manifest.json file, and pull out the relavant information.
    
    manfile is the filename and path of a manifest.json file
    
    returns a tuple ('MXD', 'ServiceName', 'ServiceURL', {'db1': [fc1, fc2, ...], ...})
    """
    mxd = ''
    service = ''
    url = ''
    databases = {}
    with open(manfile, 'r') as f:
        manifest = json.load(f)
    mxd = manifest['resources'][0]['onPremisePath']
    pathbits = manifest['resources'][0]['serverPath'].split('\\')
    servicename = [x for x in pathbits if 'MapServer' in x]
    if len(servicename) == 1:
        service = servicename[0].split('.')[0]
        for src in manifest['databases']:
            dbconfig = {x.split('=')[0]: x.split('=')[1] for x in src['onPremiseConnectionString'].split(';')}
            if 'INSTANCE' in dbconfig:
                dbname = dbconfig['DATABASE'] + ':' + dbconfig['INSTANCE']
            else:
                dbname = dbconfig['DATABASE']
            databases[dbname] = [x['onServerName'] for x in src['datasets']]
            pathpieces = pathbits[pathbits.index('arcgisinput')+1: pathbits.index(servicename[0])]
            pathpieces.append(service)
        #url = '/' + '/'.join(pathpieces)
        url = '/'.join(pathpieces)
    else:
        #some other service type, skip it
        mxd = ''
        service = ''
        url = ''
        databases = {}
    return mxd, service, url, databases

def search_services(query, services, quiet):
    """
    Search map services for the given query string.

    query is a string to search for in featureclasses, databases, maps, or service names
    services is a list of MapService objects to search through
    quiet is a value in [0, 1, 2] that determines what to return:
        0: all info
        1: name and url
        2: just url

    returns a list of string representations of the matching MapService objects.
    """
    cards = set()
    for svc in services:
        if (svc.uses_feature(query) or svc.uses_database(query) or 
            query.upper() in svc.mxd.upper() or query.upper() in svc.name.upper()):
            if quiet >= 2:
                cards.add(svc.veryquiet_repr())
            elif quiet == 1:
                cards.add(svc.quiet_repr())
            else:
                cards.add(repr(svc))
    return list(cards)

def get_args():
    """
    Handle command line arguments.

    returns the arguments namespace.
    """
    parser = argparse.ArgumentParser('Find a featureclass, database, mxd, or service in ArcGIS Server',
                                     epilog='For search strings inlcuding spaces, enclose the query in double-quotes')
    parser.add_argument('name', help='string for which to search (blank returns info on all services)',
                        nargs='?', default='')
    parser.add_argument('-q', '--quiet', help='only display service names and URLs', action='store_true')
    parser.add_argument('-qq', '--veryquiet', help='only display service URLs, comma delimited', action='store_true')
    parser.add_argument('-cs', '--configstore', help='explicitly provide full path to config store', action='store')
    parser.add_argument('-csv', '--tocsv', help='create csv output', action='store_true')
    parser.add_argument('-md', '--markdown', help='create Markdown output', action='store_true')
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    if args.configstore:
        arcdir = args.configstore
    else:
        try:
            arcdir = find_arcserver_config()
        except IOError as e:
            if e.errno == errno.ENOENT:
                print 'Cannot find ArcGIS Server configuration.'
                sys.exit(1)
            else:
                raise
    manifests = get_manifests(arcdir)
    services = []
    for manifile in manifests:
        mxd, svc, url, dbs = parse_manifest(manifile)
        if mxd != '':
            services.append(MapService(mxd, svc, url, dbs))
    if args.name == '':
        if args.veryquiet:
            print ','.join([x.veryquiet_repr() for x in services])
        else:
            if args.tocsv:
                print "Run time: {0}".format(datetime.datetime.now().strftime("%Y-%m-%d @ %I:%M:%S %p"))
                print "Service Name,Service Folder,Source MXD Path,Data Source(s)"
            for svc in services:
                if args.quiet:
                    print svc.quiet_repr()
                elif args.tocsv:
                    print svc.csv_repr()
                elif args.markdown:
                    print svc.md_repr()
                else:
                    print svc
    else:
        quietlvl = 0
        delim = '\n'
        if args.veryquiet:
            quietlvl = 2
            #delim = ','
        elif args.quiet:
            quietlvl = 1
        res = search_services(args.name, services, quietlvl)
        if len(res) > 0:
            print delim.join([svc for svc in res])
        else:
            print 'No Matches Found.'