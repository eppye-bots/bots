## How does this 'run' thing work? ##
  1. When you run bots-engine, each active route is run.
  1. Per route bots will perform all configured actions (read, translate, write):
  1. In bots-monitor you can view the results of the run(s), the incoming edi-files, the outgoing edi-files, etc.

<br>
<h2>Detailed explanation</h2>
<img src='./RouteDiagram.png' />

All actions in the picture take place in the route 'myfirstroute'.<br>
The route contains:<br>
<ul><li>an in-channel - fetches the incoming orders.<br>
</li><li>in the route is indicated that it should translate<br>
</li><li>an out-channel - transports the in-house orders to your file system.</li></ul>

<br>
When the incoming files have been read via the in-channel, bots starts to translate:<br>
<ul><li>bots parses the incoming file, using the information in the route: editype=edifact, messagetype=edifact.<br>
</li><li>as edifact is a standard bots can find out itself that the incoming edifact file contains order messages of messagetype ORDERSD96AUNEAN008<br>
</li><li>bots looks in the translation table (see <i>bots-monitor->Configuration->translations</i>) to find out what to do: what mapping script to use, to what editype and messagetype should be translated. In this case  the mapping script 'myfirstscriptordersedi2fixed' translates to editype 'fixed', messagetype 'ordersfixed'.<br>
</li><li>the mapping script is the heart of the translation. In the mapping script the data from the incoming message is fetched and place into the outgoing message.</li></ul>

<br>
A complete translation in bots needs:<br>
<ul><li>Configure of the translation (<i>bots-monitor->Configuration->Translations</i>).<br>
</li><li>A grammar for the incoming message. A grammar describes an edi-message: the records, sequence of the records, fields in the records, field lengths etc.<br>
</li><li>A mapping script. The mapping script gets data from the incoming message and puts it in the outgoing message. A mapping script is a Python script. You do not need to be proficient in Python to do this; only the basics of Python are used. And Python is a relatively easy computer language. There are a lot of good examples of mapping scripts in the plugins.<br>
</li><li>A grammar for the outgoing message.
