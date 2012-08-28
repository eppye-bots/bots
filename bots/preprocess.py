import os
import re
import zipfile
from django.utils.translation import ugettext as _
#bots-modules
import botslib
import botsglobal
from botsconfig import *

@botslib.log_session
def preprocess(routedict,function, status=FILEIN,**argv):
    ''' for preprocessing of files.
        these are NOT translations; translation involve grammars, mapping scripts etc. think of eg:
        - unzipping zipped files.
        - password protected files.
        Than the actual processing function is called.
        If errors occur during processing, no ta are left with status FILEIN !
        preprocess is called right after the in-communicatiation
    '''
    nr_files = 0
    for row in botslib.query(u'''SELECT idta,filename
                                FROM  ta
                                WHERE   idta>%(rootidta)s
                                AND     status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                AND     fromchannel=%(fromchannel)s
                                ''',
                                {'status':status,'statust':OK,'idroute':routedict['idroute'],'fromchannel':routedict['fromchannel'],'rootidta':botslib.get_minta4query()}):
        try:
            botsglobal.logmap.debug(u'Start preprocessing "%s" for file "%s".',function.__name__,row['filename'])
            ta_from = botslib.OldTransaction(row['idta'])
            ta_from.filename = row['filename']
            function(ta_from=ta_from,endstatus=status,routedict=routedict,**argv)
        except:
            txt = botslib.txtexc()
            ta_from.update(statust=ERROR,errortext=txt)
            ta_from.deletechildren()
        else:
            botsglobal.logmap.debug(u'OK preprocessing  "%s" for file "%s".',function.__name__,row['filename'])
            ta_from.update(statust=DONE)
            nr_files += 1
    return nr_files
    
@botslib.log_session
def postprocess(routedict,function, status=FILEOUT,**argv):
    ''' for postprocessing of files.
        these are NOT translations; translation involve grammars, mapping scripts etc. think of eg:
        - zip files.
        If errors occur during processing, no ta are left with status FILEOUT !
        postprocess is called right before the out-communicatiation
    '''
    nr_files = 0
    for row in botslib.query(u'''SELECT idta,filename
                                FROM  ta
                                WHERE   idta>%(rootidta)s
                                AND     status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                AND     tochannel=%(tochannel)s
                                ''',
                                {'status':status,'statust':OK,'idroute':routedict['idroute'],'tochannel':routedict['tochannel'],'rootidta':botslib.get_minta4query()}):
        try:
            botsglobal.logmap.debug(u'Start postprocessing "%s" for file "%s".',function.__name__,row['filename'])
            ta_from = botslib.OldTransaction(row['idta'])
            ta_from.filename = row['filename']
            function(ta_from=ta_from,endstatus=status,routedict=routedict,**argv)
        except:
            txt = botslib.txtexc()
            ta_from.update(statust=ERROR,errortext=txt)
            ta_from.deletechildren()
        else:
            botsglobal.logmap.debug(u'OK postprocessing  "%s" for file "%s".',function.__name__,row['filename'])
            ta_from.update(statust=DONE)
            nr_files += 1
    return nr_files

#regular expression for mailbag.
HEADER = re.compile('(\s*(ISA))|(\s*(UNA.{6})?\s*(U\s*N\s*B)s*.{1}(.{4}).{1}(.{1}))|(\s*(STX=))',re.DOTALL)
#           group:    1   2       3  4            5        6         7                8   9

def mailbag(ta_from,endstatus,**argv):
    ''' 2 main functions:
        -   recognizes and distuinguishes several edi types: x12 edifact tradacoms xml
            ('mailbag' in, correct editype out)
        -   split up interchanges (edifact, x12, tradacoms)
        details:
        - edifact, x12 and tradacoms can be can be mixed,
        - recognizes xml files; but messagetype 'xml' has a special handling when reading xml-files: xpath identifiers are used.
          this is needed for using xml in mailbag!
        - when more interchanges in one file: strongly recommended to mailbag/split these.
        - handle multiple UNA in one file, including different charsets.
        - handle multiple x12 seperators in one file.
    '''
    edifile = botslib.readdata(filename=ta_from.filename)       #read as binary...
    startpos = 0
    while (1):
        found = HEADER.search(edifile[startpos:])
        if found is None:
            if startpos:    #all ISA/UNB have been found in file; no new ISA/UNB is found. So all processing is done.
                break
            #guess if this is an xml file.....
            sniffxml = edifile[:25]
            sniffxml = sniffxml.lstrip(' \t\n\r\f\v\xFF\xFE\xEF\xBB\xBF\x00')       #to find first 'real' data; some char are because of BOM, UTF-16 etc
            if sniffxml and sniffxml[0] == '<':
                ta_to = ta_from.copyta(status=endstatus,statust=OK,filename=ta_from.filename,editype='xml',messagetype='mailbag')  #make transaction for translated message; gets ta_info of ta_frommes
                #~ ta_tomes.update(status=STATUSTMP,statust=OK,filename=ta_set_for_processing.filename,editype='xml') #update outmessage transaction with ta_info;
                break
            else:
                raise botslib.InMessageError(_(u'Found no content in mailbag.'))
        elif found.group(1):
            editype = 'x12'
            headpos = startpos + found.start(2)
            count = 0
            for char in edifile[headpos:headpos+120]:  #search first 120 characters to find separators
                if char in '\r\n' and count != 105:
                    continue
                count += 1
                if count == 4:
                    field_sep = char
                elif count == 106:
                    record_sep = char
                    break
            #~ foundtrailer = re.search(re.escape(record_sep)+'\s*IEA'+re.escape(field_sep)+'.+?'+re.escape(record_sep),edifile[headpos:],re.DOTALL)
            foundtrailer = re.search(re.escape(record_sep)+'\s*I\s*E\s*A\s*'+re.escape(field_sep)+'.+?'+re.escape(record_sep),edifile[headpos:],re.DOTALL)
        elif found.group(3):
            editype = 'edifact'
            if found.group(4):
                field_sep = edifile[startpos + found.start(4) + 4]
                record_sep = edifile[startpos + found.start(4) + 8]
                headpos = startpos + found.start(4)
            else:
                field_sep = '+'
                record_sep = "'"
                headpos = startpos + found.start(5)
            foundtrailer = re.search(re.escape(record_sep)+'\s*U\s*N\s*Z\s*'+re.escape(field_sep)+'.+?'+re.escape(record_sep),edifile[headpos:],re.DOTALL)
        elif found.group(8):
            editype = 'tradacoms'
            headpos = startpos + found.start(9)
            field_sep = '='     #the tradacoms 'after-segment-tag-seperator'
            record_sep = "'"
            foundtrailer = re.search(re.escape(record_sep)+'\s*E\s*N\s*D\s*'+re.escape(field_sep)+'.+?'+re.escape(record_sep),edifile[headpos:],re.DOTALL)
        if not foundtrailer:
            raise botslib.InMessageError(_(u'Found no valid envelope trailer in mailbag.'))
        endpos = headpos + foundtrailer.end()
        #so: interchange is from headerpos untill endpos
        #~ if HEADER.search(edifile[headpos+25:endpos]):   #check if there is another header in the interchange
            #~ raise botslib.InMessageError(u'Error in mailbag format: found no valid envelope trailer.')
        ta_to = ta_from.copyta(status=endstatus)  #make transaction for translated message; gets ta_info of ta_frommes
        tofilename = str(ta_to.idta)
        filesize = len(edifile[headpos:endpos])
        tofile = botslib.opendata(tofilename,'wb')
        tofile.write(edifile[headpos:endpos])
        tofile.close()
        ta_to.update(statust=OK,filename=tofilename,editype=editype,messagetype=editype,rsrv2=filesize) #update outmessage transaction with ta_info;
        startpos = endpos
        botsglobal.logger.debug(_(u'        File written: "%s".'),tofilename)

def botsunzip(ta_from,endstatus,password=None,pass_non_zip=False,**argv):
    ''' unzip file;
        editype & messagetype are unchanged.
    '''
    try:
        myzipfile = zipfile.ZipFile(botslib.abspathdata(filename=ta_from.filename),mode='r')
    except zipfile.BadZipfile:
        botsglobal.logger.debug(_(u'File is not a zip-file.'))
        if pass_non_zip:        #just pass the file
            botsglobal.logger.debug(_(u'"pass_non_zip" is True, just pass the file.'))
            ta_to = ta_from.copyta(status=endstatus,statust=OK)
            return
        raise botslib.InMessageError(_(u'File is not a zip-file.'))

    if password:
        myzipfile.setpassword(password)
    for info_file_in_zip in myzipfile.infolist():
        if info_file_in_zip.filename[-1] == '/':    #check if this is a dir; if so continue
            continue
        ta_to = ta_from.copyta(status=endstatus)
        tofilename = str(ta_to.idta)
        content = myzipfile.read(info_file_in_zip.filename)    #read file in zipfile
        filesize = len(content)
        tofile = botslib.opendata(tofilename,'wb')
        tofile.write(content)
        tofile.close()
        ta_to.update(statust=OK,filename=tofilename,rsrv2=filesize) #update outmessage transaction with ta_info;
        botsglobal.logger.debug(_(u'        File written: "%s".'),tofilename)
    myzipfile.close()

def botszip(ta_from,endstatus,**argv):
    ''' zip file;
        editype & messagetype are unchanged.
    '''
    ta_to = ta_from.copyta(status=endstatus)
    tofilename = str(ta_to.idta)
    pluginzipfilehandler = zipfile.ZipFile(botslib.abspathdata(filename=tofilename), 'w', zipfile.ZIP_DEFLATED)
    pluginzipfilehandler.write(botslib.abspathdata(filename=ta_from.filename),ta_from.filename)
    pluginzipfilehandler.close()
    ta_to.update(statust=OK,filename=tofilename) #update outmessage transaction with ta_info;


def extractpdf(ta_from,endstatus,**argv):
    ''' Try to extract text content of a PDF file to a csv.
        You know this is not a great idea, right? But we'll do the best we can anyway!
        Page and line numbers are added to each row.
        Columns and rows are based on the x and y coordinates of each text element within tolerance allowed.
        Multiple text elements may combine to make one field, some PDFs have every character separated!
        You may need to experiment with x_group and y_group values, but defaults seem ok for most files.
        Output csv is UTF-8 encoded - The csv module doesn't directly support reading and writing Unicode
        If the PDF is just an image, all bets are off. Maybe try OCR, good luck with that!
        Mike Griffin 14/12/2011
    '''
    from pdfminer.pdfinterp import PDFResourceManager, process_pdf
    from pdfminer.converter import TextConverter
    from pdfminer.layout import LAParams, LTContainer, LTText, LTTextBox
    import csv

    class CsvConverter(TextConverter):
        def __init__(self, *args, **kwargs):
            TextConverter.__init__(self, *args, **kwargs)

        def receive_layout(self, ltpage):

            # recursively get every text element and it's coordinates
            def render(item):
                if isinstance(item, LTContainer):
                    for child in item:
                        render(child)
                elif isinstance(item, LTText):
                    (_,_,x,y) = item.bbox

                    # group the y values (rows) within group tolerance
                    for v in yv:
                        if y > v-y_group and y < v+y_group:
                            y = v
                    yv.append(y)

                    line = lines[int(-y)]
                    line[x] = item.get_text().encode('utf-8')

            from collections import defaultdict
            lines = defaultdict(lambda : {})

            yv = []
            render(ltpage)

            lineid = 0
            for y in sorted(lines.keys()):
                line = lines[y]
                lineid += 1
                csvdata = [ltpage.pageid,lineid] # first 2 columns are page and line numbers

                # group the x values (fields) within group tolerance
                p = 0
                field_txt = ''
                for x in sorted(line.keys()):
                    gap = x - p
                    if p > 0 and gap > x_group:
                        csvdata.append(field_txt)
                        field_txt = ''
                    field_txt += line[x]
                    p = x
                csvdata.append(field_txt)
                csvout.writerow(csvdata)
            if lineid == 0:
                raise botslib.InMessageError(_(u'PDF text extraction failed, it may contain just image(s)?'))


    #get some optional parameters
    x_group = argv.get('x_group',10) # group text closer than this as one field
    y_group = argv.get('y_group',5)  # group lines closer than this as one line
    password = argv.get('password','')
    quotechar = argv.get('quotechar','"')
    field_sep = argv.get('field_sep',',')
    escape = argv.get('escape','\\')
    charset = argv.get('charset','utf-8')
    if not escape:
        doublequote = True
    else:
        doublequote = False

    try:
        pdf_stream = botslib.opendata(ta_from.filename, 'rb')
        ta_to = ta_from.copyta(status=endstatus)
        tofilename = str(ta_to.idta)
        csv_stream = botslib.opendata(tofilename,'wb')
        csvout = csv.writer(csv_stream, quotechar=quotechar, delimiter=field_sep, doublequote=doublequote, escapechar=escape)

        # Process PDF
        rsrcmgr = PDFResourceManager(caching=True)
        device = CsvConverter(rsrcmgr, csv_stream, codec=charset)
        process_pdf(rsrcmgr, device, pdf_stream, pagenos=set(), password=password, caching=True, check_extractable=True)

        device.close()
        pdf_stream.close()
        csv_stream.close()
        filesize = os.path.getsize(botslib.abspathdata(tofilename))
        ta_to.update(statust=OK,filename=tofilename,rsrv2=filesize) #update outmessage transaction with ta_info;
        botsglobal.logger.debug(_(u'        File written: "%s".'),tofilename)
    except:
        txt = botslib.txtexc()
        botsglobal.logger.error(_(u'PDF extraction failed, may not be a PDF file? Error:\n%s'),txt)
        raise botslib.InMessageError(_(u'PDF extraction failed, may not be a PDF file? Error:\n$error'),error=txt)


