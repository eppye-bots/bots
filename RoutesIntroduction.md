## Introduction ##

> Definition: _A route is a workflow for edi-files_ <br></li></ul>

A route determines where to get the incoming files, what to do with these edi-files (translate!) and their destination.<br>
'Routes' are the most important concept in configuring bots.<br>
Routes are independent: an edi-file in a route stays in that route.<br>
Route are configured in <i>bots-monitor->Configuration->Routes</i>.<br>
<br>
<br>
<blockquote><i>Schema of a simple route</i><br>
<img src='./RouteDiagram2.png' />
<br>
<br>
To get a route like this working the following must be configured:<br>
</blockquote><ul><li>the route itself in <i>bots-monitor->Configuration->Routes</i>.<br>
</li><li>an in-channel for incoming edi files.<br>
</li><li>an out-channel for outgoing edi files.<br>
</li><li>the <a href='TranslationIntroduction.md'>translation</a>.</li></ul>


The route above is a simple route; files come from one source,  there is one translation, one destination.<br>
More options are possible using <a href='RoutesComposite.md'>composite routes</a>
