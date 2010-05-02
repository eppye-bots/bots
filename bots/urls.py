from django.conf.urls.defaults import *
from django.contrib import admin,auth
from django.views.generic.simple import redirect_to
from django.contrib.auth.decorators import login_required,user_passes_test
from bots import views

admin.autodiscover()
staff_required = user_passes_test(lambda u: u.is_staff)
superuser_required = user_passes_test(lambda u: u.is_superuser)

urlpatterns = patterns('',
    (r'^login.*', 'django.contrib.auth.views.login'),
    (r'^logout.*', 'django.contrib.auth.views.logout',{'next_page': '/home/'}),
    #login required
    (r'^about.*', login_required(views.about)),
    (r'^help.*', login_required(views.help)),
    (r'^incoming.*', login_required(views.incoming)),
    (r'^detail.*', login_required(views.detail)),
    (r'^process.*', login_required(views.process)),
    (r'^outgoing.*', login_required(views.outgoing)),
    (r'^document.*', login_required(views.document)),
    (r'^reports.*', login_required(views.reports)),
    (r'^confirm.*', login_required(views.confirm)),
    (r'^filer.*', login_required(views.filer)),
    #only staff
    (r'^admin/$', 'bots.views.index'),  #do not show django admin root page
    (r'^admin/bots/$', 'bots.views.index'),  #do not show django admin root page
    (r'^admin/bots/uniek/.+$', redirect_to, {'url': '/admin/bots/uniek/'}),  #hack. uniek counters can be changed (on main page), but never added. This rule disables the edit/add uniek pages. 
    (r'^admin/(.*)', staff_required(admin.site.root)),
    (r'^runengine.+', staff_required(views.runengine)),
    #only superuser
    (r'^delete.*', superuser_required(views.delete)),
    (r'^plugin.*', superuser_required(views.plugin)),
    (r'^plugout.*', superuser_required(views.plugout)),
    (r'^unlock.*', superuser_required(views.unlock)),
    (r'^sendtestmail.*', superuser_required(views.sendtestmailmanagers)),
    #catch-all
    (r'^.*', 'bots.views.index'), 
    )
