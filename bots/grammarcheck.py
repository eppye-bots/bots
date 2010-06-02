import sys
import os
import botsinit
import botslib
import grammar

def showusage():
    print
    print "    Usage:  %s  -c<directory> <editype> <messagetype>"%os.path.basename(sys.argv[0])
    print
    print "    Checks a Bots grammar."
    print "    Same checks are used as in translations with bots-engine."
    print "    Searches for grammar in regular place: bots/usersys/grammars/<editype>/<messagetype>.py"
    print "    Options:"
    print "        -c<directory>   directory for configuration files (default: config)."
    print "    Example:"
    print "        %s -cconfig  edifact  ORDERSD96AUNEAN008"%os.path.basename(sys.argv[0])
    print
    sys.exit(0)

def startmulti(grammardir,editype):
    import glob
    botslib.initconfigurationfile('config')
    botslib.initlogging()
    for g in glob.glob(grammardir):
        g1 = os.path.basename(g)
        g2 = os.path.splitext(g1)[0]
        if g1 in ['__init__.py']:
            continue
        if g1.startswith('edifact'):
            continue
        if g1.startswith('records') or g1.endswith('records.py'):
            continue
        try:
            grammar.grammarread(editype,g2)
        except:
            #~ print 'Found error in grammar:',g
            print botslib.txtexc()
            print '\n'
        else:
            print 'OK - no error found in grammar',g,'\n'
        
def start():
    #********command line arguments**************************
    editype =''
    messagetype = ''
    botsinifile = 'config'
    for arg in sys.argv[1:]:
        if not arg:
            continue
        if arg.startswith('-c'):
            botsinifile = arg[2:]
            if not botsinifile:
                print '    !!Indicated Bots should use specific .ini file but no file name was given.'
                showusage()
        elif arg in ["?", "/?"] or arg.startswith('-'):
            showusage()
        else:
            if not editype:
                editype = arg
            else:
                messagetype = arg
    if not (editype and messagetype):
        print '    !!Both editype and messagetype are required.'
        showusage()
    #********end handling command line arguments**************************

    try:
        botslib.initconfigurationfile(botsinifile)
        botslib.initlogging()
        grammar.grammarread(editype,messagetype)
    except:
        print 'Found error in grammar:'
        print botslib.txtexc()
    else:
        print 'OK - no error found in grammar'


if __name__=='__main__':
    start()
