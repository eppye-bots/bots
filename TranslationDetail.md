## How translations work ##

Best understood by looking at this schema:
> ![./MappingScheme.png](./MappingScheme.png)
<br></li></ul>

Step-by-step:<br>
<ol><li>The edi file is lexed and parsed using the <a href='GrammarsIntroduction.md'>grammar</a>.<br>
</li><li>The message is transformed into a tree structure. This is similar to the use of DOM in xml. Advantages:<br>
<ul><li>easy access to message content. This is quite similar to XML-queries or X-path.<br>
</li><li>choose the logic for the mapping script that is best fit for the situation - instead of being forced to 'loop' over incoming message.<br>
</li><li>Sorting: eg. sort article lines by article number.<br>
</li><li>Counting: eg. count number of lines, total amounts etc<br>
</li><li>Access the data you already written in the tree<br>
</li></ul></li><li><a href='ConfigurationSplit.md'>Split</a> the edi file into separate messages (eg one edi file can contain multiple orders).<br>
</li><li>Find the <a href='TranslationRules.md'>right translation</a> for message.<br>
</li><li>Run the <a href='MappingIntroduction.md'>mapping script</a> for message.<br>
</li><li>Serialize the outmessage-tree to file. This is checked and formatted according to the <a href='GrammarsIntroduction.md'>grammar</a> of the outgoing message.<br>
</li><li>Outgoing messages are <a href='ConfigurationMerge.md'>enveloped and/or merged</a>.
