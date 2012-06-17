import os
import sys
import copy
import inmessage
import outmessage
import botslib
import botsinit
import botsglobal
from botsconfig import *

#buggy
#in usersys/grammars/xmlnocheck should be a file xmlnocheck
#usage: c:\python25\python  bots-xml2botsgrammar.py  botssys/infile/test.xml   botssys/infile/resultgrammar.py  -cconfig


def treewalker(node_instance,mpath):
    mpath.append({'BOTSID':node_instance.record['BOTSID']})
    for childnode in node_instance.children:
        yield childnode,mpath[:]
        for terugnode,terugmpath in treewalker(childnode,mpath):
            yield terugnode,terugmpath 
    mpath.pop()
    

def writefields(tree,node_instance,mpath):
    putmpath = copy.deepcopy(mpath)
    #~ print mpath
    #~ print node_instance.record
    for key in node_instance.record.keys():
        #~ print key
        if key not in ['BOTSID','BOTSIDnr']:
            putmpath[-1][key]=u'dummy'
            #~ print 'mpath used',mpath
            #~ putmpath = copy.deepcopy(mpath)
    tree.put(*putmpath)
            #~ del mpath[-1][key]
    #~ print '\n'
        
def tree2grammar(node_instance,structure,recorddefs):
    structure.append({ID:node_instance.record['BOTSID'],MIN:0,MAX:99999,LEVEL:[]})
    recordlist = []
    for key in node_instance.record.keys():
        recordlist.append([key, 'C', 256, 'AN'])
    if node_instance.record['BOTSID'] in recorddefs:
        recorddefs[node_instance.record['BOTSID']] = removedoublesfromlist(recorddefs[node_instance.record['BOTSID']] + recordlist)
        #~ recorddefs[node_instance.record['BOTSID']].extend(recordlist)
    else:
        recorddefs[node_instance.record['BOTSID']] = recordlist
    for childnode in node_instance.children:
        tree2grammar(childnode,structure[-1][LEVEL],recorddefs)

def recorddefs2string(recorddefs,sortedstructurelist):
    recorddefsstring = "{\n"
    for i in sortedstructurelist:
    #~ for key, value in recorddefs.items():
        recorddefsstring += "    '%s':\n        [\n"%i
        for field in recorddefs[i]:
            if field[0]=='BOTSID':
                field[1]='M'
                recorddefsstring += "        %s,\n"%field
                break
        for field in recorddefs[i]:
            if '__' in field[0]:
                recorddefsstring += "        %s,\n"%field
        for field in recorddefs[i]:
            if field[0] not in ['BOTSID','BOTSIDnr'] and '__' not in field[0]:
                recorddefsstring += "        %s,\n"%field
        recorddefsstring += "        ],\n"
    recorddefsstring += "    }\n"
    return recorddefsstring
    
def structure2string(structure,level=0):
    structurestring = ""
    for i in structure:
        structurestring += level*"    " + "{ID:'%s',MIN:%s,MAX:%s"%(i[ID],i[MIN],i[MAX])
        recursivestructurestring = structure2string(i[LEVEL],level+1)
        if recursivestructurestring:
            structurestring += ",LEVEL:[\n" + recursivestructurestring + level*"    " + "]},\n"
        else:
            structurestring += "},\n"
    return structurestring

def structure2list(structure):
    structurelist = structure2listcore(structure)
    return removedoublesfromlist(structurelist)
    
def removedoublesfromlist(orglist):
    list2return = []
    for e in orglist:
        if e not in list2return:
            list2return.append(e)
    return list2return

def structure2listcore(structure):
    structurelist = []
    for i in structure:
        structurelist.append(i[ID])
        structurelist.extend(structure2listcore(i[LEVEL]))
    return structurelist

def showusage():
    print
    print 'Usage:'
    print '    %s   -c<directory>  <xml_file>  <xml_grammar_file>'%os.path.basename(sys.argv[0])
    print
    print '    Creates a grammar from an xml file.'
    print '    Options:'
    print "        -c<directory>      directory for configuration files (default: config)."
    print '        <xml_file>         name of the xml file to read'
    print '        <xml_grammar_file> name of the grammar file to write'
    print
    sys.exit(0)
    
def start():
    #********command line arguments**************************
    edifile =''
    grammarfile = ''
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
            if not edifile:
                edifile = arg
            else:
                grammarfile = arg
    if not (edifile and grammarfile):
        print '    !!Both edifile and grammarfile are required.'
        showusage()

    #********end handling command line arguments**************************
    editype='xmlnocheck'
    messagetype='xmlnocheckxxxtemporaryforxml2grammar'
    mpath = []
    
    botsinit.generalinit(configdir)
    os.chdir(botsglobal.ini.get('directories','botspath'))
    botsinit.initenginelogging()
    
    #the xml file is parsed as an xmlnocheck message....so a (temp) xmlnocheck grammar is needed....without content... this file is not removed....
    tmpgrammarfile = botslib.join(botsglobal.ini.get('directories','usersysabs'),'grammars',editype,messagetype+'.py')
    f = open(tmpgrammarfile,'w')
    f.close()

    inn = inmessage.edifromfile(editype=editype,messagetype=messagetype,filename=edifile)
    #~ inn.root.display()
    out = outmessage.outmessage_init(editype=editype,messagetype=messagetype,filename='botssys/infile/unitnode/output/inisout03.edi',divtext='',topartner='')    #make outmessage object
    
    #handle root
    rootmpath = [{'BOTSID':inn.root.record['BOTSID'],'BOTSIDnr':'1'}]
    out.put(*rootmpath)
    #~ out.root.display()
    writefields(out,inn.root,rootmpath)
    #walk tree; write results to out-tree
    for node_instance,mpath in treewalker(inn.root,mpath):
        mpath.append({'BOTSID':node_instance.record['BOTSID']})
        if out.get(*mpath) is None:
            out.put(*mpath)
        writefields(out,node_instance,mpath)
        
    #~ out.root.display()
    
    #out-tree is finished; represents ' normalised' tree suited for writing as a grammar
    structure = []
    recorddefs = {}
    tree2grammar(out.root,structure,recorddefs)
    #~ for key,value in recorddefs.items():
        #~ print key,value
        #~ print '\n'
    sortedstructurelist = structure2list(structure)
    recorddefsstring = recorddefs2string(recorddefs,sortedstructurelist)
    structurestring = structure2string(structure)
    
    #write grammar file
    grammar = open(grammarfile,'wb')
    grammar.write('#grammar automatically generated by bots open source edi translator.')
    grammar.write('\n')
    grammar.write('from bots.botsconfig import *')
    grammar.write('\n\n')
    grammar.write('syntax = {}')
    grammar.write('\n\n')
    grammar.write('structure = [\n%s]\n'%(structurestring))
    grammar.write('\n\n')
    grammar.write('recorddefs = %s'%(recorddefsstring))
    grammar.write('\n\n')
    grammar.close()
    print 'grammar file is written',grammarfile

if __name__ == '__main__':
    start()
    
