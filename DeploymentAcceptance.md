w### Isolated acceptance testing (bots>=3.0) ###
This is a 'mode' for testing which is **isolated**:
  * no external communication: all I/O is from/to file system
  * system state does not change (eg no increased counters, no test runs in system, etc)
Idea is to run an acceptance test without affecting your system (or the system of your edi-partner).

**Note**: all plugins since 20130101 are suited for isolated acceptances tests.

<br>
<h3>Advantages</h3>
<ol><li>Isolated acceptance tests are 'repeatable' (because same counters are used, same time is used etc). This is great for testing: each run of a test gives the same results. This makes it easy to compared the results automatically.<br>
</li><li>By using isolated acceptance tests your test-environment can be equal to production-environment. So you can use standard directory comparison tools to push changes test->production.<br>
</li><li>As the acceptance tests are isolated, this means an acceptance test can be run in a production-environment without affecting this environment. This way you can verify that after a change, all still runs as before in your production environment.</li></ol>

<br>
<h3>Running isolated acceptance tests</h3>
<ol><li>in all channels set 'testpath'. Testpath should point to a directory with test-files.<br>
</li><li>Set option 'runacceptancetest' in bots.ini to 'True'.<br>
</li><li>Run 'new'<br>
</li><li>Check results of run with what you expect<br>
</li><li>Delete  runs/files from acceptance test (menu:Systasks->Bulk delete; select <b>only</b> 'Delete transactions in acceptance testing'.)</li></ol>

<br>
<h3>Acceptance tests in plugins</h3>
Plugins since 20130101 can be run as acceptance tests.<br>
About the plugins with build-in acceptance test:<br>
<ul><li>'testpath' for incoming files are in botssys\infile<br>
</li><li>'testpath' for outgoing files go to botssys\outfile<br>
</li><li>each plugin also contains the the expected outgoing files (botssys\infile\outfile); these are used to compare the results.<br>
</li><li>included is a route script (bots/usersys/routescripts/bots_acceptancetest.py):<br>
<ul><li>before run: discard directory 'botssys\outfile'.<br>
</li><li>after run: global run results are compared with expectation (#in, #out. #errors, etc)<br>
</li><li>after run: compare files in botssys\outfile with expected files in botssys\infile\outfile<br>
</li><li>the output of these comparisons can be seen in terminal ('dos-box')</li></ul></li></ul>

<br>
<h3>Implementation Details</h3>
What bots does when running an isolated acceptance test:<br>
<ul><li>channel-type is set to 'file'.<br>
</li><li>channel-path is set to the value in 'testpath'. if testpath is empty: use path.<br>
</li><li>channel-remove is set to 'off': no deletion of incoming files.<br>
</li><li>error-email: not send.<br>
</li><li>fixed date/time in envelopes and in mappings (if function transform.strftime() is used)<br>
</li><li>counters/references: fixed; counters are not incremented<br>
</li><li>incoming files are always read in same order.<br>
</li><li>outgoing-filename options: date/time is fixed<br>
</li><li>no archiving<br>
</li><li>additional user exits are run. User exits are in file usersys/routescripts/botsacceptancetest.py :<br>
<ul><li>before run:: function pretest. use eg to empty out-directories etc<br>
</li><li>after run: function post-test. This can be used to check results, compare files etc<br>
After running an isolated acceptance test, the reports/filereports/data-files/etc generated during acceptance-testing can be deleted via: menu:Systasks->Bulk delete; select <b>only</b> 'Delete transactions in acceptance testing'.</li></ul></li></ul>

Implementation remarks:<br>
<ul><li>GUI does not have the results of post-test script (runs after automaticmaintanance); view this in terminal/dos-box.<br>
</li><li>communication scripts: script should check explicitly if in acceptance test and act accordingly.<br>
</li><li>database communication: script should check explicitly if in acceptance test and act accordingly.
