"""
sef2bots.py

Command line params: sourcefile.sef targetfile.py

Optional command line params: -seq, -struct

Converts a SEF grammar into a Bots grammar. If targetfile exists (and is writeable),
it will be overwritten.

If -seq is specified, field names in record definitions will be
sequential (TAG01, TAG02, ..., where TAG is the record tag) instead of
the 'normal' field names.

If -struct is specified, only the Bots grammar variable 'structure' will be
constructed, i.e. the 'recorddefs' variable will be left out.

Parses the .SETS, .SEGS, .COMS and .ELMS sections. Any other sections are ignored.

(Mostly) assumes correct SEF syntax. May well break on some syntax errors.

If there are multiple .SETS sections, only the last one is processed. If there are
multiple message definitions in the (last) .SETS section, only the last one is
processed.

If there are multiple definitions of a segment, only the first one is taken
into account.

If there are multiple definitions of a field, only the last one is taken into
account.

Skips ^ and ignores .!$-&*@ in segment/field refs.
Also ignores syntax rules and dependency notes.

Changes seg max of '>1' to 99999 and elm maxlength to 99999 if 0 or > 99999
If you don't like that, change the 'constants' MAXMAX and/or MAXLEN below
"""

MAXMAX = 99999 # for dealing with segs/groups with max '>1'
MAXLEN = 99999 # for overly large elm maxlengths
TAB = '    '

import sys
import os
import copy
import atexit
import traceback

def showusage(scriptname):
    print "Usage: python %s [-seq] [-nostruct] [-norecords] sourcefile targetfile" % scriptname
    print "    Convert SEF grammar in <sourcefile> into Bots grammar in <targetfile>."
    print "    Option -seq : use sequential numbered fields in record definitions instead of field names/ID's."
    print "    Option -nostruct : the 'structure' will not be written."
    print "    Option -norecords : the 'records' will not be written."
    print 
    sys.exit(0)

class SEFError(Exception):
    pass

class StructComp(object):
    """ For components of the Bots grammar variable 'structure' """
    def __init__(self, tag, min, max, sub = None):
        self.id = tag
        self.min = min
        self.max = max
        if sub:
            self.sub = sub
        else:
            self.sub = []
    def tostring(self, tablevel = 0):
        s = tablevel*TAB + "{ID: '%s', MIN: %d, MAX: %d" % (self.id, self.min, self.max)
        if self.sub:
            s += ", LEVEL: [\n" \
                   + ",\n".join([subcomp.tostring(tablevel + 1) for subcomp in self.sub]) + "," \
                   + "\n" + tablevel * TAB + "]"
        s += "}"
        return s

class RecDef(object):
    """ For records/segments; these end up in the Bots grammar variable 'recorddefs' """
    def __init__(self, tag, sub = None):
        self.id = tag
        if sub:
            self.sub = sub
        else:
            self.sub = []
    def tostring(self, useseq = False, tablevel = 0):
        return tablevel*TAB + \
                "'%s': [\n"%(self.id) + \
                "\n".join([c.tostring(useseq, tablevel+1) for c in self.sub]) +\
                "\n" + \
                tablevel*TAB + "],"

class FieldDef(object):
    """ For composite and non-composite fields """
    def __init__(self, tag, req = 'C', minlen = '', maxlen = '', type = 'AN', sub = None, freq = 1, seq = None):
        self.id = tag
        self.req = req
        self.minlen = minlen
        self.maxlen = maxlen
        self.type = type
        self.sub = sub
        if not sub:
            self.sub = []
        self.freq = freq
        self.seq = seq
    def tostring(self, useseq = False, tablevel = 0):
        if not useseq:
            fldname = self.id
        else:
            fldname = self.seq
        if not self.sub:
            if self.minlen.strip() == '1':
                return tablevel * TAB + "['%s', '%s', %s, '%s']" %\
                       (fldname, self.req, self.maxlen, self.type) + ","
            else:
                return tablevel * TAB + "['%s', '%s', (%s, %s), '%s']" %\
                       (fldname, self.req, self.minlen, self.maxlen, self.type) + ","            
        else:
            return tablevel * TAB + "['%s', '%s', [\n" % (fldname, self.req) \
                   + "\n".join([field.tostring(useseq, tablevel + 1) for field in self.sub]) \
                   + "\n" + tablevel * TAB + "]],"
        
def split2(line, seps):
    """
    Split <line> on whichever character in <seps> occurs in <line> first.
    Return pair (line_up_to_first_sep_found, first_sep_found_plus_rest_of_line)
    If none of <seps> occurs, return pair ('', <line>)
    """
    i = 0
    length = len(line)
    while i < length and line[i] not in seps:
        i += 1
    if i == length:
        return '', line
    return line[:i], line[i:]
    
def do_set(line):
    """
    Reads the (current) .SETS section and converts it into a Bots grammar 'structure'.
    Returns the *contents* of the structure, as a string.
    """
    definition = line.split('=')
    line = definition[1].lstrip('^')
    comps = readcomps(line)
    tree = comps[0]
    tree.sub = comps[1:]
    return tree.tostring()

def readcomps(line):
    """ Reads all components from a .SETS line, and returns them in a nested list """
    comps = []
    while line:
        comp, line = readcomp(line)
        comps.append(comp)
    #~ displaystructure(comps)
    return comps

def displaystructure(comps,tablevel=0):
    for i in comps:
        print tablevel*TAB, i.id,i.min,i.max
        if i.sub:
            displaystructure(i.sub,tablevel+1)


def readcomp(line):
    """
    Reads a component, which can be either a segment or a segment group.
    Returns pair (component, rest_of_line)
    """
    discard, line = split2(line, "[{")
    if not line:
        return None, ''
    if line[0] == '[':
        return readseg(line)
    if line[0] == '{':
        return readgroup(line)
    raise SEFError("readcomp() - unexpected character at start of: %s" % line)

def readseg(line):
    """ Reads a single segment. Returns pair (segment, rest_of_line) """
    discard, line = line.split('[', 1)
    segstr, line = line.split(']', 1)
    components = segstr.split(',')
    num = len(components)
    maxstr = ''
    if num == 3:
        tag, req, maxstr = components
    elif num == 2:
        tag, req = components
    elif num == 1:
        tag, req = components[0], 'C'
    if req == 'M':
        min = 1
    else:
        min = 0
    if tag[0] in ".!$-&":
        tag = tag[1:]
    if '*' in tag:
        tag = tag.split('*')[0]
    if '@' in tag:
        tag = tag.split('@')[0]
    if tag.upper() == 'LS':
        print "LS segment found"
    if not maxstr:
        max = 1
    elif maxstr == '>1':
        max = MAXMAX
        print "Changed max for seg '%s' to %d (orig. %s)" % (tag, MAXMAX, maxstr)
    else:
        max = int(maxstr)
    return StructComp(tag, min, max), line

def readgroup(line):
    """ Reads a segment group. Returns pair (segment_group, rest_of_line) """
    discard, line = line.split('{', 1)
    #~ print '>>',line
    tag, line = split2(line, ':+-[{')
    #~ print '>>',tag,'>>',line
    maxstr = ''
    if line[0] == ':':   # next element can be group.max
        maxstr, line = split2(line[1:], '+-[{')
    #~ print '>>',line
    discard, line = split2(line, "[{")
    group = StructComp(tag, 0, 0) # dummy values for group. This is later on adjusted
    done = False
    while not done:
        if not line or line[0] == '}':
            done = True
        else:
            comp, line = readcomp(line)
            group.sub.append(comp)
    if group.sub:
        header = group.sub[0]
        group.id = header.id    #use right tag for header segment
        if header.min > group.min:
            group.min = header.min
        group.sub = group.sub[1:]
    if not maxstr:
        group.max = 1
    else:
        if maxstr != '>1':
            group.max = int(maxstr)
        else:
            group.max = MAXMAX
            if tag:
                oldtag = tag
            else:
                oldtag = group.id
            print "Changed max for group '%s' to %d (orig. %s)" % (oldtag, MAXMAX, maxstr)
    return group, line[1:]

def comdef(line, issegdef = False):
    """
    Reads segment or composite definition (syntactically identical; defaults to composite).
    Returns RecDef (for segment) or FieldDef (for composite)
    """
    tag, spec = line.split('=')
    if issegdef:
        com = RecDef(tag)
    else:
        com = FieldDef(tag)
    com.sub = getfields(spec)[0]
    return com

def getfields(line, isgroup = False):
    """ Returns pair (fieldlist, rest_of_line) """
    if isgroup and line[0] == '}':
        return [], line[1:]
    if not isgroup and not line:
        return [], ''
    if not isgroup and line[0] in ",+":
        return [], line[1:]
    if line[0] == '[':
        field, line = getfield(line[1:])
        multifield = [field]
        for i in range(1, field.freq):
            extrafield = copy.deepcopy(field)
            extrafield.req = 'C'
            multifield.append(extrafield)
        fields, line = getfields(line, isgroup)
        return multifield + fields, line
    if line[0] == '{':
        multstr, line = split2(line[1:], "[{")
        if not multstr:
            mult = 1
        else:
            mult = int(multstr)
        group, line = getfields(line, True)
        repgroup = []
        for i in range(mult):
            repgroup += copy.deepcopy(group)
        fields, line = getfields(line, isgroup)
        return repgroup + fields, line

def getfield(line):
    """ Returns pair (single_field_ref, rest_of_line) """
    splits = line.split(']', 1)
    field = fielddef(splits[0])
    if len(splits) == 1:
        return field, ''
    return field, splits[1]

def fielddef(line):
    """
    Get a field's tag, its req (M or else C), its min and max lengths, and its frequency (repeat count).
    Return FieldDef
    """
    if line[0] in ".!$-&":
        line = line[1:]
    if ',' not in line:
        req, freq = 'C', 1
    else:
        splits = line.split(',')
        num = len(splits)
        if num == 3:
            line, req, freq = splits
            freq = int(freq)
        elif num == 2:
            (line, req), freq = splits, 1
        else:
            line, req, freq = splits[0], 'C', 1
        if req != 'M':
            req = 'C'
    if ';' not in line:
        lenstr = ''
    else:
        line, lenstr = line.split(';')
    if '@' in line:
        line, discard = line.split('@', 1)
    if not lenstr:
        minlen = maxlen = ''
    else:
        if ':' in lenstr:
            minlen, maxlen = lenstr.split(':')
        else:
            minlen = lenstr
    return FieldDef(line, req = req, minlen = minlen, maxlen = maxlen, freq = freq)        

def elmdef(line):
    """ Reads elm definition (min and max lengths and data type), returns FieldDef """
    tag, spec = line.split('=')
    type, minlenstr, maxlenstr = spec.split(',')
    try:
        maxlen = int(maxlenstr)
    except ValueError:
        maxlen = 0
    if maxlen == 0 or maxlen > MAXLEN:
        print "Changed max length for elm '%s' to %d (orig. %s)" % (tag, MAXLEN, maxlenstr)
        maxlenstr = str(MAXLEN)
    elm = FieldDef(tag, minlen = minlenstr, maxlen = maxlenstr, type = type)
    return elm

def getelmsinfo(elms, coms):
    """
    Get types and lengths from elm defs into com defs,
    and rename multiple occurrences of subfields
    """
    for comid in coms:
        com = coms[comid]
        counters = {}
        sfids = [sf.id for sf in com.sub]
        for i, sfield in enumerate(com.sub):
            sfield.seq = "%02d" % (i + 1)
            if sfield.id not in elms:
                raise SEFError("getelmsinfo() - no subfield definition found for element '%s'" % sfield.id)
            elm = elms[sfield.id]
            if not sfield.minlen:
                sfield.minlen = elm.minlen
            if not sfield.maxlen:
                sfield.maxlen = elm.maxlen
            sfield.type = elm.type
            if sfield.id not in counters:
                counters[sfield.id] = 1
            else:
                counters[sfield.id] += 1
            if counters[sfield.id] > 1 or sfield.id in sfids[i + 1:]:
                sfield.id += "#%d" % counters[sfield.id]
            
def getfieldsinfo(elms, coms, segs):
    """
    Get types and lengths from elm defs and com defs into seg defs,
    and rename multiple occurrences of fields. Also rename subfields
    of composites to include the name of their parents.
    Finally, add the necessary BOTSID element.
    """
    for seg in segs:
        counters = {}
        fids = [f.id for f in seg.sub]
        for i, field in enumerate(seg.sub):
            field.seq = "%s%02d" % (seg.id, i + 1)
            iscomposite = False
            if field.id in elms:
                elm = elms[field.id]
                field.type = elm.type
                if not field.minlen:
                    field.minlen = elm.minlen
                if not field.maxlen:
                    field.maxlen = elm.maxlen
            elif field.id in coms:
                iscomposite = True
                com = coms[field.id]
                field.sub = copy.deepcopy(com.sub)
            else:
                raise SEFError("getfieldsinfo() - no field definition found for element '%s'" % field.id)
            if not field.id in counters:
                counters[field.id] = 1
            else:
                counters[field.id] += 1
            if counters[field.id] > 1 or field.id in fids[i + 1:]:
                field.id += "#%d" % counters[field.id]
            if iscomposite:
                for sfield in field.sub:
                    sfield.id = field.id + '.' + sfield.id
                    sfield.seq = field.seq + '.' + sfield.seq
        seg.sub.insert(0, FieldDef('BOTSID', req = 'M', minlen = "1", maxlen = "3", type = "AN", seq = 'BOTSID'))
        
def convertfile(infile, outfile, useseq, nostruct, norecords,edifactversionID):
    struct = ""
    segdefs, segdict, comdefs, elmdefs = [], {}, {}, {}
    #        segdict just keeps a list of segs already found, so they don't get re-defined
    in_sets = in_segs = in_coms = in_elms = False
    #*******reading sef grammar***********************
    for line in infile:
        line = line.strip('\n')
        if line:
            if line[0] == '*':  # a comment, skip
                pass
            elif line[0] == '.':
                line = line.upper()
                in_sets = in_segs = in_coms = in_elms = False
                if line == '.SETS':
                    in_sets = True
                elif line == '.SEGS':
                    in_segs = True
                elif line == '.COMS':
                    in_coms = True
                elif line == '.ELMS':
                    in_elms = True
            else:
                if in_sets:
                    struct = do_set(line)
                elif not norecords:    #if record need to be written
                    if in_segs:
                        seg = comdef(line, issegdef = True)
                        # if multiple defs for this seg, only do first one
                        if seg.id not in segdict:
                            segdict[seg.id] = 1
                            segdefs.append(seg)
                    elif in_coms:
                        com = comdef(line)
                        comdefs[com.id] = com
                    elif in_elms:
                        elm = elmdef(line)
                        elmdefs[elm.id] = elm
    #*****writing bots grammar **************
    outfile.write('from bots.botsconfig import *\n')
    if not nostruct:  #if structure: need syntax
        outfile.write('from edifactsyntax3 import syntax\n')
    if norecords:  #if record need to import thee
        outfile.write('from records%s import recorddefs\n\n'%edifactversionID)
    #****************************************
    if not nostruct: 
        outfile.write("\nstructure = [\n%s\n]\n" % struct)
    if not norecords:
        getelmsinfo(elmdefs, comdefs)
        getfieldsinfo(elmdefs, comdefs, segdefs)
        outfile.write("\nrecorddefs = {\n%s\n}\n" % "\n".join([seg.tostring(useseq) for seg in segdefs]))

def start(args):
    useseq, nostruct, norecords, infilename, outfilename = False, False, False, None, None
    for arg in args:
        if not arg:
            continue
        if arg in ["-h", "--help", "?", "/?", "-?"]:
            showusage(args[0].split(os.sep)[-1])
        if arg == "-seq":
            useseq = True
        elif arg == "-nostruct":
            nostruct = True
        elif arg == "-norecords":
            norecords = True
        elif not infilename:
            infilename = arg
        elif not outfilename:
            outfilename = arg
        else:
            showusage(args[0].split(os.sep)[-1])
    if not infilename or not outfilename:
        showusage(args[0].split(os.sep)[-1])
    #************************************
    
    infile = open(infilename, 'r')
    outfile = open(outfilename, 'w')
    edifactversionID = os.path.splitext(os.path.basename(outfilename))[0][6:]
    print '    Convert sef->bots "%s".'%(outfilename)
    convertfile(infile, outfile, useseq, nostruct, norecords,edifactversionID)
    infile.close()
    outfile.close()

if __name__ == "__main__":
    try:
        start(sys.argv[1:])
    except:
        traceback.print_exc()
    else:
        print "Done"
