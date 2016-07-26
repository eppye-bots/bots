# The setup in my\_first\_plugin #

<br>
<h2>Look at the configured route</h2>
To view the route configured: <i>bots-monitor->Configuration->Routes</i><br>
This will look like:<br>
<img src='./StartRoutes.png' />

A route tells bots what to do: where to get the edi-files, what type of files these are (this determines the translation done), and where to put the translated edi-files..<br>
One route is configured, called 'myfirstfoute'.<br>
The route uses communication channel 'myfirstroute_in' to get incoming edi-files.<br>
These are edifact format: fromeditype=edifact, frommessagetype=edifact.<br>
Bots will figure out the exact messagetype (like ORDERSD96AUN) by itself.<br>
The translated edi-files (fixed format) go to communication channel 'myfirstroute_out'.<br>
<br>
<br>
<h2>View the communication channels</h2>
To view the communication channels configured: <i>bots-monitor->Configuration->Channels</i><br>
This will look like:<br>
<img src='./StartChannels.png' />

A communications channel communicates edi-files in or out of bots.<br>
There are different types of channels, eg: file, ftp, smtp, pop3, etc.<br>
In this plugin 2 routes are configured. Both are type 'file': all reading and writing is to file system.<br>
There is one 'in'-channel and one 'out'-channel.<br>
Channels for file-system require a path and a filename.<br>
<br>
<br>
<h2>The translations in this configuration</h2>
To view the translations configured: <i>bots-monitor->Configuration->Translations</i><br>
This will look like:<br>
<img src='./StartTranslations.png' />

There is one <a href='TranslationIntroduction.md'>translation</a> configured.<br>
This translation translates edi messages of editype 'edifact' and messagetype 'ORDERSD96AUNEAN008' using mappingscript 'myfirstscriptordersedi2fixed' to edi messages of editype 'fixed' and messagetype 'ordersfixed'.<br>
<br>
Each messagetype has a <a href='GrammarsIntroduction.md'>grammar</a> which describes the message: records, fields, formats. The grammar is a file; you can find it in:<br>
<i>C:\Python27\Lib\site-packages\bots\usersys\grammars\fixed</i><br>

The <a href='MappingIntroduction.md'>mapping</a> script does the actual translation; basically it gets data from the incoming message and puts the data in the outgoing message.<br>
The mapping script is a file; you can find it in:<br>
<i>C:\Python27\Lib\site-packages\bots\usersys\mappings\edifact</i><br>
