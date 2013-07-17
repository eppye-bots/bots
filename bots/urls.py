from django.conf.urls.defaults import patterns,include   #depreciated in 1.5
#~ from django.conf.urls import patterns,include           #does not work in django 1.3
from django.contrib import admin
#~ from django.views.generic.base import RedirectView
from django.contrib.auth.decorators import login_required,user_passes_test
import views

admin.autodiscover()
staff_required = user_passes_test(lambda u: u.is_staff)
superuser_required = user_passes_test(lambda u: u.is_superuser)
run_permission = user_passes_test(lambda u: u.has_perm('bots.change_mutex'))

urlpatterns = patterns('',
    (r'^login.*', 'django.contrib.auth.views.login', {'template_name': 'admin/login.html'}),
    (r'^logout.*', 'django.contrib.auth.views.logout',{'next_page': '/'}),
    #login required
    (r'^home.*', login_required(views.home)),
    (r'^incoming.*', login_required(views.incoming)),
    (r'^detail.*', login_required(views.detail)),
    (r'^process.*', login_required(views.process)),
    (r'^outgoing.*', login_required(views.outgoing)),
    (r'^document.*', login_required(views.document)),
    (r'^reports.*', login_required(views.reports)),
    (r'^confirm.*', login_required(views.confirm)),
    (r'^filer.*', login_required(views.filer)),
    (r'^srcfiler.*', login_required(views.srcfiler)),
    #only staff
    (r'^admin/$', login_required(views.home)),  #do not show django admin root page
    (r'^admin/bots/$', login_required(views.home)),  #do not show django admin root page
    (r'^admin/', include(admin.site.urls)),
    (r'^runengine.+', run_permission(views.runengine)),
    #only superuser
    (r'^delete.*', superuser_required(views.delete)),
    (r'^plugin/index.*', superuser_required(views.plugin_index)),
    (r'^plugin.*', superuser_required(views.plugin)),
    (r'^plugout/index.*', superuser_required(views.plugout_index)),
    (r'^plugout/backup.*', superuser_required(views.plugout_backup)),
    (r'^plugout.*', superuser_required(views.plugout)),
    (r'^sendtestmail.*', superuser_required(views.sendtestmailmanagers)),
    #catch-all
    (r'^.*', 'bots.views.index'),
    )

handler500 = 'bots.views.server_error'
