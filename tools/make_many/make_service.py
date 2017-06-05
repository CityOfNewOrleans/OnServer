import argparse
import os
import sys
import time

import arcpy

def get_args():
    desc = 'Automagically Create a MapService from an MXD.'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('MXD', help='Full path to map document to use for service creation')
    parser.add_argument('URL', help='Server URL for the resulting MapService')
    parser.add_argument('Connection', help='Path to an ArcGIS Server connection file')
    return parser.parse_args()

def pretty_print_msgs(messages):
    outmsgs = []
    for key in ['errors', 'warnings', 'messages']:
        outmsgs.append('   + {0}'.format(key))
        if len(messages[key]) > 0:
            for ((msg, code), layers) in messages[key].iteritems():
                if len(layers) > 0:
                    outmsgs.append('     \\ {0}: {1}'.format(msg, ','.join([x.name for x in layers])))
                else:
                    outmsgs.append('     \\ {0}'.format(msg))
    print '\n'.join(outmsgs)

if __name__ == '__main__':
    start = time.time()
    args = get_args()
    if os.path.exists(args.MXD) and os.path.isfile(args.MXD):
        print 'Creating {0}...'.format(args.URL)
        mapdoc = arcpy.mapping.MapDocument(args.MXD)
        draftdoc = os.path.join(os.path.abspath('.'), os.path.basename(args.MXD)) + '.sddraft'
        if '/' in args.URL:
            folder = '/'.join(args.URL.split('/')[:-1])
            service = args.URL.split('/')[-1]
        else:
            folder = None
            service = args.URL[:]
        print ' - generating draft service definition...'
        msgs = arcpy.mapping.CreateMapSDDraft(mapdoc, draftdoc, service, 'ARCGIS_SERVER', args.Connection, False, folder)
        if len(msgs['errors']) > 0:
            print ' - errors creating service definition:'
            pretty_print_msgs(msgs)
            sys.exit(1)
        else:
            print ' - map analysis messages:'
            pretty_print_msgs(msgs)
    else:
        print ' - cannot create map service.'
        print '   + Map {0} does not exist.'.format(args.MXD)
        sys.exit(1)

    print ' - staging draft service definition...'
    servicedef = draftdoc.replace('.sddraft', '.sd')
    arcpy.StageService_server(draftdoc, servicedef)

    print ' - publishing service...'
    arcpy.UploadServiceDefinition_server(servicedef, args.Connection)
    os.unlink(servicedef)

    print 'Complete in {0:.2f} seconds.\n'.format(time.time()-start)