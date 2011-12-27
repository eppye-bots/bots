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
    ''' for pre- and postprocessing of files.
        these are NOT translations; translation involve grammars, mapping scripts etc. think of eg:
        - unzipping zipped files.
        - convert excel to csv
        - password protected files.
        Select files from INFILE -> SET_FOR_PROCESSING using criteria
        Than the actual processing function is called.
        The processing function does: SET_FOR_PROCESSING -> PROCESSING -> FILEIN
        If errors occur during processing, no ta are left with status FILEIN !
        preprocess is called right after the in-communicatiation
    '''
    nr_files = 0
    preprocessnumber = botslib.getpreprocessnumber()
    if not botslib.addinfo(change={'status':preprocessnumber},where={'status':status,'idroute':routedict['idroute'],'fromchannel':routedict['fromchannel']}):    #check if there is something to do
        return 0
    for row in botslib.query(u'''SELECT idta,filename,charset
                                FROM  ta
                                WHERE   idta>%(rootidta)s
                                AND     status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                AND     fromchannel=%(fromchannel)s
                                ''',
                                {'status':preprocessnumber,'statust':OK,'idroute':routedict['idroute'],'fromchannel':routedict['fromchannel'],'rootidta':botslib.get_minta4query()}):
        try:
            botsglobal.logmap.debug(u'Start preprocessing "%s" for file "%s".',function.__name__,row['filename'])
            ta_set_for_processing = botslib.OldTransaction(row['idta'])
            ta_processing = ta_set_for_processing.copyta(status=preprocessnumber+1)
            ta_processing.filename=row['filename']
            function(ta_from=ta_processing,endstatus=status,routedict=routedict,**argv)
        except:
            txt=botslib.txtexc()
            ta_processing.failure()
            ta_processing.update(statust=ERROR,errortext=txt)
        else:
            botsglobal.logmap.debug(u'OK preprocessing  "%s" for file "%s".',function.__name__,row['filename'])
            ta_set_for_processing.update(statust=DONE)
            ta_processing.update(statust=DONE)
            nr_files += 1
    return nr_files


header = re.compile('(\s*(ISA))|(\s*(UNA.{6})?\s*(U\s*N\s*B)s*.{1}(.{4}).{1}(.{1}))',re.DOTALL)
#           group:    1   2       3  4            5        6         7

def mailbag(ta_from,endstatus,**argv):
    ''' split 'mailbag' files to separate files each containing one interchange (ISA-IEA or UNA/UNB-UNZ).
        handles x12 and edifact; these can be mixed.
        recognizes xml files. messagetype 'xml' has a special handling when reading xml-files.

        about auto-detect/mailbag:
        - in US mailbag is used: one file for all received edi messages...appended in one file. I heard that edifact and x12 can be mixed,
            but have actually never seen this.
        - bots needs a 'splitter': one edi-file, more interchanges. it is preferred to split these first.
        - handle multiple UNA in one file, including different charsets.
        - auto-detect: is is x12, edifact, xml, or??
    '''
    edifile = botslib.readdata(filename=ta_from.filename)       #read as binary...
    startpos=0
    while (1):
        found = header.search(edifile[startpos:])
        if found is None:
            if startpos:    #ISA/UNB have been found in file; no new ISA/UNB is found. So all processing is done.
                break
            #guess if this is an xml file.....
            sniffxml = edifile[:25]
            sniffxml = sniffxml.lstrip(' \t\n\r\f\v\xFF\xFE\xEF\xBB\xBF\x00')       #to find first ' real' data; some char are because of BOM, UTF-16 etc
            if sniffxml and sniffxml[0]=='<':
                ta_to=ta_from.copyta(status=endstatus,statust=OK,filename=ta_from.filename,editype='xml',messagetype='mailbag')  #make transaction for translated message; gets ta_info of ta_frommes
                #~ ta_tomes.update(status=STATUSTMP,statust=OK,filename=ta_set_for_processing.filename,editype='xml') #update outmessage transaction with ta_info;
                break;
            else:
                raise botslib.InMessageError(_(u'Found no content in mailbag.'))
        elif found.group(1):
            editype='x12'
            headpos=startpos+ found.start(2)
            count=0
            for c in edifile[headpos:headpos+120]:  #search first 120 characters to find separators
                if c in '\r\n' and count!=105:
                    continue
                count +=1
                if count==4:
                    field_sep = c
                elif count==106:
                    record_sep = c
                    break
            #~ foundtrailer = re.search(re.escape(record_sep)+'\s*IEA'+re.escape(field_sep)+'.+?'+re.escape(record_sep),edifile[headpos:],re.DOTALL)
            foundtrailer = re.search(re.escape(record_sep)+'\s*I\s*E\s*A\s*'+re.escape(field_sep)+'.+?'+re.escape(record_sep),edifile[headpos:],re.DOTALL)
        elif found.group(3):
            editype='edifact'
            if found.group(4):
                field_sep = edifile[startpos + found.start(4) + 4]
                record_sep = edifile[startpos + found.start(4) + 8]
                headpos=startpos+ found.start(4)
            else:
                field_sep = '+'
                record_sep = "'"
                headpos=startpos+ found.start(5)
            foundtrailer = re.search(re.escape(record_sep)+'\s*U\s*N\s*Z\s*'+re.escape(field_sep)+'.+?'+re.escape(record_sep),edifile[headpos:],re.DOTALL)
        if not foundtrailer:
            raise botslib.InMessageError(_(u'Found no valid envelope trailer in mailbag.'))
        endpos = headpos+foundtrailer.end()
        #so: interchange is from headerpos untill endpos
        #~ if header.search(edifile[headpos+25:endpos]):   #check if there is another header in the interchange
            #~ raise botslib.InMessageError(u'Error in mailbag format: found no valid envelope trailer.')
        ta_to = ta_from.copyta(status=endstatus)  #make transaction for translated message; gets ta_info of ta_frommes
        tofilename = str(ta_to.idta)
        tofile = botslib.opendata(tofilename,'wb')
        tofile.write(edifile[headpos:endpos])
        tofile.close()
        ta_to.update(statust=OK,filename=tofilename,editype=editype,messagetype=editype) #update outmessage transaction with ta_info;
        startpos=endpos
        botsglobal.logger.debug(_(u'        File written: "%s".'),tofilename)

def botsunzip(ta_from,endstatus,password=None,pass_non_zip=False,**argv):
    ''' unzip file;
        editype & messagetype are unchanged.
    '''
    try:
        z = zipfile.ZipFile(botslib.abspathdata(filename=ta_from.filename),mode='r')
    except zipfile.BadZipfile:
        botsglobal.logger.debug(_(u'File is not a zip-file.'))
        if pass_non_zip:        #just pass the file
            botsglobal.logger.debug(_(u'"pass_non_zip" is True, just pass the file.'))
            ta_to = ta_from.copyta(status=endstatus,statust=OK)
            return
        raise botslib.InMessageError(_(u'File is not a zip-file.'))
        
    if password:
        z.setpassword(password)
    for f in z.infolist():
        if f.filename[-1] == '/':    #check if this is a dir; if so continue
            continue
        ta_to = ta_from.copyta(status=endstatus)
        tofilename = str(ta_to.idta)
        tofile = botslib.opendata(tofilename,'wb')
        tofile.write(z.read(f.filename))
        tofile.close()
        ta_to.update(statust=OK,filename=tofilename) #update outmessage transaction with ta_info; 
        botsglobal.logger.debug(_(u'        File written: "%s".'),tofilename)

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
                field_txt=''
                for x in sorted(line.keys()):
                    gap = x - p
                    if p > 0 and gap > x_group:
                        csvdata.append(field_txt)
                        field_txt=''
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
        ta_to.update(statust=OK,filename=tofilename) #update outmessage transaction with ta_info; 
        botsglobal.logger.debug(_(u'        File written: "%s".'),tofilename)
    except:
        txt=botslib.txtexc()
        botsglobal.logger.error(_(u'PDF extraction failed, may not be a PDF file? Error:\n%s'),txt)
        raise botslib.InMessageError(_(u'PDF extraction failed, may not be a PDF file? Error:\n$error'),error=txt)


def extractexcel(ta_from,endstatus,**argv):
    ''' extract excel file.
        editype & messagetype are unchanged.
    '''
    #***functions used by extractexcel
    #-------------------------------------------------------------------------------
    def read_xls(infilename):
        # Read excel first sheet into a 2-d array
        book       = xlrd.open_workbook(infilename)
        sheet      = book.sheet_by_index(0)
        formatter  = lambda(t,v): format_excelval(book,t,v,False)
        xlsdata = []
        for row in range(sheet.nrows):
            (types, values) = (sheet.row_types(row), sheet.row_values(row))
            xlsdata.append(map(formatter, zip(types, values)))
        return xlsdata
    #-------------------------------------------------------------------------------
    def dump_csv(xlsdata, tofilename):
        stream = botslib.opendata(tofilename, 'wb')
        csvout = csv.writer(stream, quotechar=quotechar, delimiter=field_sep, doublequote=doublequote, escapechar=escape)
        csvout.writerows( map(utf8ize, xlsdata) )
        stream.close()
    #-------------------------------------------------------------------------------
    def format_excelval(book, type, value, wanttupledate):
        #  Clean up the incoming excel data for some data types
        returnrow = []
        if   type == 2:
            if value == int(value): 
                value = int(value)
        elif type == 3:
            datetuple = xlrd.xldate_as_tuple(value, book.datemode)
            value = datetuple if wanttupledate else tupledate_to_isodate(datetuple)
        elif type == 5:
            value = xlrd.error_text_from_code[value]
        return value
    #-------------------------------------------------------------------------------
    def tupledate_to_isodate(tupledate):
        # Turns a gregorian (year, month, day, hour, minute, nearest_second) into a
        # standard YYYY-MM-DDTHH:MM:SS ISO date.
        (y,m,d, hh,mm,ss) = tupledate
        nonzero = lambda n: n!=0
        date = "%04d-%02d-%02d"  % (y,m,d)    if filter(nonzero, (y,m,d))                else ''
        time = "T%02d:%02d:%02d" % (hh,mm,ss) if filter(nonzero, (hh,mm,ss)) or not date else ''
        return date+time
    #-------------------------------------------------------------------------------
    def utf8ize(l):
        # Make string-like things into utf-8, leave other things alone
        return [unicode(s).encode("utf-8") if hasattr(s,'encode') else s for s in l]
    #***end functions used by extractexcel
    import xlrd
    import csv
    #get some parameters for csv-format; default are as initial setup by Mike
    quotechar = argv.get('quotechar','"')
    field_sep = argv.get('field_sep',',')
    escape = argv.get('escape','\\')
    if not escape:
        doublequote = True
    else: 
        doublequote = False
    try:
        infilename = botslib.abspathdata(ta_from.filename)
        xlsdata = read_xls(infilename)
        ta_to = ta_from.copyta(status=endstatus)
        tofilename = str(ta_to.idta)
        dump_csv(xlsdata,tofilename)
        ta_to.update(statust=OK,filename=tofilename) #update outmessage transaction with ta_info; 
        botsglobal.logger.debug(_(u'        File written: "%s".'),tofilename)
    except:
        txt=botslib.txtexc()
        botsglobal.logger.error(_(u'Excel extraction failed, may not be an Excel file? Error:\n%s'),txt)
        raise botslib.InMessageError(_(u'Excel extraction failed, may not be an Excel file? Error:\n$error'),error=txt)

