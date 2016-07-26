# Composite routes #

## Introduction ##
A simple route reads the edi files from one inchannel, translates, and sends the translated files to one outchannel.<br>
More flexibility is offered by the use of composite routes.<br>
In a composite route there are several entries in the routes screen, each with the same 'idroute' but a different 'seq' (sequence number within route). Each entry (with different 'seq') is called <b>route-part</b>.<br>
Best way to use this is to have each route-part do one thing; either:<br>
<ul><li>fetch incoming files; you can fetch files from multiple sources<br>
</li><li>translate (typically once per route)<br>
</li><li>send outgoing files to different destinations/partners using <a href='RoutesComposite#Filtering.md'>filtering</a>
It is advised to set up composite routes this way (using at least 3 route-parts).</li></ul>

<br>
<h2>Use cases</h2>
<ul><li>Send edi files via ftp where each partner has its own ftp-server.<br>
</li><li>Confirmations/acknowledgements: acknowledgements for incoming edi-files are routed back to the sender (filter by editype/messagetype).<br>
</li><li>Fetch from multiple sources, eg ftp-servers of different partners..<br>
</li><li>Route to different internal destinations: invoices to another system than ASN's (filter by messagetype)<br>
</li><li>Use a VAN, but one partner uses AS2 (filter by partner)<br>
</li><li>Incoming files are translated multiple times, each message-type goes to different destination. Eg: translate orders both to in-house file (import ERP) and an HTML-email (for viewing).</li></ul>

<br>
<h2>Example plugin</h2>
Download <a href='http://sourceforge.net/projects/bots/files/plugins/'>the plugin demo_composite_route</a><br>
This plugin has one composite route consisting of:<br>
<ul><li>2 input parts<br>
</li><li>translate part<br>
</li><li>3 output parts, using filtering<br>
Detailled description <a href='PluginList.md'>here</a></li></ul>

<br>
<h2>Filtering for different outchannels</h2>
You can filter per outchannel; eg send only asn's through this outchannel.<br>
In route-screen (<i>bots-monitor->Configuration->Routes</i>) the fields used for filtering under 'Filtering for outchannel'.<br>
If eg <i>toeditype=csv</i>, only csv-files will be send over the outchannel.<br>
NOTE: if filtering is not specified, all outgoing files in the route are send through the outchannel.<br>
<br>
<br>
<h2>Schematic</h2>
Schematic overview of a route consisting of 5 parts:<br>
<img src='./RouteDiagramComp.png' />
<br>
<br>
Note:<br>
<ul><li>if no inchannel in route-part nothing comes in for that route-part.<br>
</li><li>if 'translate' in a route-part is off, no translation in that route-part.<br>
</li><li>if no outchannel in route-part nothing goes out for that route-part.
