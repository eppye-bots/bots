## Code conversion ##
Bots supports code conversions. The code conversion is done in a mapping script; maintenance for the codes can be done via _bots-monitor->Configuration->User codes as list_.<br>

This page contains 3 examples of code conversions:<br>
<ol><li>convert currency code list.<br>
</li><li>convert internal article code to buyers article code.<br>
</li><li>convert internal article code to description.</li></ol>

<br>
<h3>Code maintenance in GUI</h3>
First configure 2 code lists (<i>bots-monitor->Configuration->user codes by type</i>):<br>
<img src='./CCbytype.png' />

<br>
Make the code conversions (<i>bots-monitor->Configuration->user codes as list</i>):<br>
<img src='./CCaslist.png' />

<br>
<h3>Code conversion in mapping script</h3>
<pre><code>    import bots.transform as transform<br>
<br>
    #convert currency code<br>
    our_currency_code = inn.get({'BOTSID':'HEA','VALUTA':None})<br>
    converted_currency_code = transform.ccode('Currency',our_currency_code)<br>
<br>
    #convert internal article code to buyers article code:<br>
    buyer_article_number = transform.ccode('LookupArticleNumber',our_article_number)<br>
<br>
    #get description (in field 'attr1') for article<br>
    description = transform.ccode('LookupArticleNumber',our_article_number,field='attr1')<br>
<br>
    #code conversion also works via reverse lookup:<br>
    our_article_number = transform.reverse_ccode('LookupArticleNumber',buyer_article_number)<br>
</code></pre>

<br>
<h3>Codeconversion functions</h3>

<h4>transform.ccode(codelist, value, field, safe)</h4>
Convert 'value' to value in 'field' using a user-maintained code list.<br>
Parameters:<br>
<ul><li>codelist: codelist as in <i>bots-monitor->Configuration->user codes by type</i>.<br>
</li><li>value to be converted (should be in 'leftcode')<br>
</li><li>field: the field to lookup (if not specified: 'rightcode')<br>
</li><li>safe: if False (default): raise exception when value is in found in codelist. If True: just return 'value'.<br>
Example of usage for leftcode to rightcode:<br>
<pre><code>    transform.ccode('articles','8712345678906') <br>
</code></pre>
Example of usage for leftcode to attr1:<br>
<pre><code>    transform.ccode('articles','8712345678906','attr1') <br>
</code></pre></li></ul>

<h4>transform.reverse_ccode(codelist, value, field)</h4>
as transform.ccode(), but conversion is from 'rightcode' to 'field'.<br>

<br>
<h3>Changes in codeconversion functions</h3>

Note: These functions have changed over versions. The old functions are deprecated but still work.<br>
<table><thead><th> <b>bots<2.1</b> </th><th> <b>bots<3.0</b> </th><th> <b>bots>=3.0</b> </th></thead><tbody>
<tr><td>codetconversion  </td><td>ccode            </td><td>ccode             </td></tr>
<tr><td>safecodetconversion</td><td>safe_ccode       </td><td>ccode with parameter safe=True</td></tr>
<tr><td>rcodetconversion </td><td>reverse_ccode    </td><td>reverse_ccode     </td></tr>
<tr><td>safercodetconversion</td><td>safe_reverse_ccode</td><td>reverse_ccode with parameter safe=True</td></tr>
