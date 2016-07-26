Channels take care of communication: file I/O, ftp, email, etc.<br>
A channel is either incoming or outgoing.<br>
Examples of channels:<br>
<ul><li>receive email from a pop3-mailbox<br>
</li><li>send to a ftp-server<br>
</li><li>pick up in-house invoices from a directory on your computer<br>
</li><li>put orders in a file queue for import in your application.</li></ul>

<blockquote>Example of communication channels for bots:<br>
<img src='./ChannelScheme.png' /></blockquote>

Notes on naming conventions:<br>
<ul><li>incoming = incoming to bots<br>
</li><li>outgoing = going out bots<br>
</li><li>inbound = my organization receives<br>
</li><li>outbound = going out of my organization</li></ul>

<br>
Note: Bots does client communicates (no server). If you need a communication server (eg for ftp, as2), use a separate server.
