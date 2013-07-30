''' converts xml file to a bots grammar.
    Note: in usersys/grammars/xmlnocheck should be a file xmlnocheck
    Usage: c:\python25\python  bots-xml2botsgrammar.py  botssys/infile/test.xml   botssys/infile/resultgrammar.py  -cconfig
    Try to have a 'completely filled' xml file.
'''
import os
import sys
import atexit
import copy
import inmessage
import outmessage
import logging
import botslib
import botsinit
import botsglobal
from botsconfig import *

#***functions for mapping******************************************
def map_treewalker(node_instance,mpath):
    ''' Generator function.
        
    '''
    mpath.append({'BOTSID':node_instance.record['BOTSID']})
    for childnode in node_instance.children:
        yield childnode,mpath[:]
        for terugnode,terugmpath in map_treewalker(childnode,mpath):
            yield terugnode,terugmpath
    mpath.pop()


def map_writefields(node_out,node_in,mpath):
    ''' als fields of this level are written to node_out.
    '''
    mpath_with_all_fields = copy.deepcopy(mpath)     #use a copy of mpath (do not want to change it)
    for key in node_in.record.keys():       
        if key in ['BOTSID','BOTSIDnr']:    #skip these
            continue
        mpath_with_all_fields[-1][key] = u'dummy'    #add key to the mpath
    node_out.put(*mpath_with_all_fields)            #write all fields.

#***functions for generating grammar from tree******************************************
def tree2grammar(node_instance,structure,recorddefs):
    structure.append({ID:node_instance.record['BOTSID'],MIN:0,MAX:99999,LEVEL:[]})
    recordlist = []
    for key in node_instance.record.keys():
        recordlist.append([key, 'C', 256, 'AN'])
    if node_instance.record['BOTSID'] in recorddefs:
        recorddefs[node_instance.record['BOTSID']] = removedoublesfromlist(recorddefs[node_instance.record['BOTSID']] + recordlist)
    else:
        recorddefs[node_instance.record['BOTSID']] = recordlist
    for childnode in node_instance.children:
        tree2grammar(childnode,structure[-1][LEVEL],recorddefs)

def recorddefs2string(recorddefs,sortedstructurelist):
    recorddefsstring = "{\n"
    for i in sorted(recorddefs):
    #~ for key, value in recorddefs.items():
        recorddefsstring += "    '%s':\n        [\n"%i
        for field in recorddefs[i]:
            if field[0] == 'BOTSID':
                field[1] = 'M'
                recorddefsstring += "        %s,\n"%field
                break
        for field in recorddefs[i]:
            if field[0].startswith(i + '__'):
                recorddefsstring += "        %s,\n"%field
        for field in sorted(recorddefs[i]):
            if field[0] not in ['BOTSID','BOTSIDnr','BOTSCONTENT'] and not field[0].startswith(i + '__'):
                recorddefsstring += "        %s,\n"%field
        recorddefsstring += "        ],\n"
    recorddefsstring += "    }\n"
    return recorddefsstring

def structure2string(structure,level=0):
    structurestring = ''
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
    for member in orglist:
        if member not in list2return:
            list2return.append(member)
    return list2return

def structure2listcore(structure):
    structurelist = []
    for i in structure:
        structurelist.append(i[ID])
        structurelist.extend(structure2listcore(i[LEVEL]))
    return structurelist


def start():
    #********command line arguments**************************
    usage = '''
    This is "%(name)s" version %(version)s, part of Bots open source edi translator (http://bots.sourceforge.net).
    Creates a grammar from an xml file.'
    Usage:'
        %(name)s  -c<directory>  <xml_file>  <xml_grammar_file>
    Options:
        -c<directory>      directory for configuration files (default: config).
        <xml_file>         name of the xml file to read
        <xml_grammar_file> name of the grammar file to write
    
    '''%{'name':os.path.basename(sys.argv[0]),'version':botsglobal.version}
    configdir = 'config'
    edifile =''
    grammarfile = ''
    for arg in sys.argv[1:]:
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print 'Error: configuration directory indicated, but no directory name.'
                sys.exit(1)
        elif arg in ["?", "/?",'-h', '--help'] or arg.startswith('-'):
            print usage
            sys.exit(0)
        else:
            if not edifile:
                edifile = arg
            else:
                grammarfile = arg
    if not edifile or not grammarfile:
        print 'Error: both edifile and grammarfile are required.'
        sys.exit(0)
    #***end handling command line arguments**************************
    botsinit.generalinit(configdir)     #find locating of bots, configfiles, init paths etc.
    process_name = 'xml2botsgrammar'
    botsglobal.logger = botsinit.initenginelogging(process_name)
    atexit.register(logging.shutdown)
    
    #the xml file is parsed as an xmlnocheck message
    editype = 'xmlnocheck'
    messagetype = 'xmlnocheckxxxtemporaryforxml2grammar'
    #a (temp) xmlnocheck grammar is needed (but needs not actual content. This file is not removed.
    tmpgrammarfile = botslib.join(botsglobal.ini.get('directories','usersysabs'),'grammars',editype,messagetype+'.py')
    filehandler = open(tmpgrammarfile,'w')
    filehandler.close()
    
    #make inmessage object: read the xml file
    inn = inmessage.parse_edi_file(editype=editype,messagetype=messagetype,filename=edifile,remove_empties_from_xml=False)
    #make outmessage object; nothing is 'filled' yet.
    out = outmessage.outmessage_init(editype=editype,messagetype=messagetype,filename='botssys/infile/unitnode/output/inisout03.edi',divtext='',topartner='')    
    
    #***do the mapping***************************************************
    #handle root
    mpath_root = [{'BOTSID':inn.root.record['BOTSID'],'BOTSIDnr':'1'}]
    out.put(*mpath_root)
    map_writefields(out,inn.root,mpath_root)
    
    #walk tree; write results to out-tree
    mpath_start = []
    for node_instance,mpath in map_treewalker(inn.root,mpath_start):
        mpath.append({'BOTSID':node_instance.record['BOTSID']})
        if out.get(*mpath) is None:     #if node does not exist: write it.
            out.put(*mpath)
        map_writefields(out,node_instance,mpath)

    #***mapping is done; out-tree is finished; represents 'normalised' tree suited for writing as a grammar
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
    print 'grammar file is written:',grammarfile

if __name__ == '__main__':
    start()

