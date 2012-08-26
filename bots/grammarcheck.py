import sys
import os
import botsinit
import botslib
import grammar

def showusage():
    print
    print "    Usage:  %s  -c<directory> <editype> <messagetype>"%os.path.basename(sys.argv[0])
    print "       or   %s  -c<directory> <path to grammar>"%os.path.basename(sys.argv[0])
    print
    print "    Checks a Bots grammar."
    print "    Same checks are used as in translations with bots-engine."
    print "    Searches for grammar in regular place: bots/usersys/grammars/<editype>/<messagetype>.py"
    print "        (even if a path is passed)"
    print "    Options:"
    print "        -c<directory>   directory for configuration files (default: config)."
    print "    Examples:"
    print "        %s -cconfig  edifact  ORDERSD96AUNEAN008"%os.path.basename(sys.argv[0])
    print "        %s -cconfig  C:/python27/lib/site-packages/bots/usersys/grammars/edifact/ORDERSD96AUNEAN008.py"%os.path.basename(sys.argv[0])
    print
    sys.exit(0)

def startmulti(grammardir,editype):
    ''' used in seperate tool for bulk checking of gramamrs while developing edifact->botsgramamrs '''
    import glob
    botsinit.generalinit('config')
    botsinit.initenginelogging()
    for filename in glob.glob(grammardir):
        filename_basename = os.path.basename(filename)
        filename_noextension = os.path.splitext(filename_basename)[0]
        if filename_basename in ['__init__.py']:
            continue
        if filename_basename.startswith('edifact'):
            continue
        if filename_basename.startswith('records') or filename_basename.endswith('records.py'):
            continue
        try:
            grammar.grammarread(editype,filename_noextension)
        except:
            print botslib.txtexc()
            print '\n'
        else:
            print 'OK - no error found in grammar',filename,'\n'

def start():
    #********command line arguments**************************
    editype =''
    messagetype = ''
    configdir = 'config'
    for arg in sys.argv[1:]:
        if not arg:
            continue
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print '    !!Indicated Bots should use specific .ini file but no file name was given.'
                showusage()
        elif arg in ["?", "/?"] or arg.startswith('-'):
            showusage()
        else:
            if os.path.isfile(arg):
                p1,p2 = os.path.split(arg)
                editype = os.path.basename(p1)
                messagetype,ext = os.path.splitext(p2)
                messagetype = str(messagetype)
                print 'grammarcheck',editype,messagetype
            elif not editype:
                editype = arg
            else:
                messagetype = arg
    if not (editype and messagetype):
        print '    !!Both editype and messagetype, or a file path, are required.'
        showusage()
    #********end handling command line arguments**************************

    try:
        botsinit.generalinit(configdir)
        botsinit.initenginelogging()
        grammar.grammarread(editype,messagetype)
    except:
        print 'Found error in grammar: ',botslib.txtexc()
    else:
        print 'OK - no error found in grammar'


if __name__ == '__main__':
    start()
