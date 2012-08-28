''' Bots configuration for django's admin site.'''
import django
from django.utils.translation import ugettext as _
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
#***********
import models
import botsglobal


class BotsAdmin(admin.ModelAdmin):
    ''' all classes in this module arre sub-classed from BotsAdmin.
    '''
    list_per_page = botsglobal.ini.getint('settings','adminlimit',botsglobal.ini.getint('settings','limit',30))
    save_as = True
    def activate(self, request, queryset):
        ''' admin action.'''
        for obj in queryset:
            obj.active = not obj.active
            obj.save()
    activate.short_description = _(u'activate/de-activate')

#*****************************************************************************************************
class CcodeAdmin(BotsAdmin):
    list_display = ('ccodeid','leftcode','rightcode','attr1','attr2','attr3','attr4','attr5','attr6','attr7','attr8')
    list_display_links = ('ccodeid',)
    list_filter = ('ccodeid',)
    ordering = ('ccodeid','leftcode')
    search_fields = ('ccodeid__ccodeid','leftcode','rightcode','attr1','attr2','attr3','attr4','attr5','attr6','attr7','attr8')
    def lookup_allowed(self, lookup, *args, **kwargs):
        if lookup.startswith('ccodeid'):
            return True
        return super(CcodeAdmin, self).lookup_allowed(lookup, *args, **kwargs)
admin.site.register(models.ccode,CcodeAdmin)

class CcodetriggerAdmin(BotsAdmin):
    list_display = ('ccodeid','ccodeid_desc',)
    list_display_links = ('ccodeid',)
    ordering = ('ccodeid',)
    search_fields = ('ccodeid','ccodeid_desc')
admin.site.register(models.ccodetrigger,CcodetriggerAdmin)

class ChannelAdmin(BotsAdmin):
    list_display = ('idchannel', 'inorout', 'type','host', 'port', 'username', 'secret', 'path', 'filename', 'remove', 'archivepath','rsrv2','ftpactive', 'ftpbinary','askmdn', 'syslock', 'starttls','apop')
    list_filter = ('inorout','type')
    ordering = ('idchannel',)
    search_fields = ('idchannel', 'inorout', 'type','host', 'username', 'path', 'filename', 'archivepath')
    fieldsets = (
        (None,          {'fields': ('idchannel', ('inorout','type'), ('host','port'), ('username', 'secret'), ('path', 'filename'), 'remove', 'archivepath', 'desc')
                        }),
        (_(u'FTP specific data'),{'fields': ('ftpactive', 'ftpbinary', 'ftpaccount' ),
                         'classes': ('collapse',)
                        }),
        (_(u'Advanced'),{'fields': (('lockname', 'syslock'), 'parameters', 'starttls','apop','askmdn','rsrv2'),
                         'classes': ('collapse',)
                        }),
    )
admin.site.register(models.channel,ChannelAdmin)

class ConfirmruleAdmin(BotsAdmin):
    actions = ('activate',)
    list_display = ('active','negativerule','confirmtype','ruletype', 'frompartner', 'topartner','idroute','idchannel','editype','messagetype')
    list_display_links = ('confirmtype',)
    list_filter = ('active','confirmtype','ruletype')
    search_fields = ('confirmtype','ruletype', 'frompartner__idpartner', 'topartner__idpartner', 'idroute', 'idchannel__idchannel', 'editype', 'messagetype')
    ordering = ('confirmtype','ruletype')
    fieldsets = (
        (None, {'fields': ('active','negativerule','confirmtype','ruletype','frompartner', 'topartner','idroute','idchannel',('editype','messagetype'))}),
        )
admin.site.register(models.confirmrule,ConfirmruleAdmin)

class MailInline(admin.TabularInline):
    model = models.chanpar
    fields = ('idchannel','mail', 'cc')
    extra = 1

class MyPartnerAdminForm(django.forms.ModelForm):
    ''' customs form for partners to check if group has groups'''
    class Meta:
        model = models.partner
    def clean(self):
        super(MyPartnerAdminForm, self).clean()
        if self.cleaned_data['isgroup'] and self.cleaned_data['group']:
            raise django.forms.util.ValidationError(_(u'A group can not be part of a group.'))
        return self.cleaned_data

class PartnerAdmin(BotsAdmin):
    actions = ('activate',)
    form = MyPartnerAdminForm
    fields = ('active', 'isgroup', 'idpartner', 'name','mail','cc','group')
    filter_horizontal = ('group',)
    inlines = (MailInline,)
    list_display = ('active','isgroup','idpartner', 'name','mail','cc')
    list_display_links = ('idpartner',)
    list_filter = ('active','isgroup')
    ordering = ('idpartner',)
    search_fields = ('idpartner','name','mail','cc')
admin.site.register(models.partner,PartnerAdmin)

class RoutesAdmin(BotsAdmin):
    actions = ('activate',)
    list_display = ('active','idroute','seq','fromchannel','fromeditype','frommessagetype','alt','frompartner','topartner','translateind','tochannel','defer','toeditype','tomessagetype','frompartner_tochannel','topartner_tochannel','testindicator','notindefaultrun','rsrv1','rsrv2')
    list_display_links = ('idroute',)
    list_filter = ('idroute','active','fromeditype')
    ordering = ('idroute','seq')
    search_fields = ('idroute', 'fromchannel__idchannel','fromeditype', 'frommessagetype', 'alt', 'tochannel__idchannel','toeditype', 'tomessagetype')
    fieldsets = (
        (None,      {'fields':  ('active',('idroute', 'seq'),'fromchannel', ('fromeditype', 'frommessagetype'),'translateind','tochannel','desc')}),
        (_(u'Filtering for outchannel'),{'fields':('toeditype', 'tomessagetype','frompartner_tochannel', 'topartner_tochannel', 'testindicator'),
                    'classes':  ('collapse',)
                    }),
        (_(u'Advanced'),{'fields':  ('alt','frompartner','topartner','notindefaultrun','defer','rsrv1','rsrv2'),
                     'classes': ('collapse',)
                    }),
    )
admin.site.register(models.routes,RoutesAdmin)

class MyTranslateAdminForm(django.forms.ModelForm):
    ''' customs form for translations to check if entry exists (unique_together not validated right (because of null values in partner fields))'''
    class Meta:
        model = models.translate
    def clean(self):
        super(MyTranslateAdminForm, self).clean()
        blub = models.translate.objects.filter(fromeditype=self.cleaned_data['fromeditype'],
                                            frommessagetype=self.cleaned_data['frommessagetype'],
                                            alt=self.cleaned_data['alt'],
                                            frompartner=self.cleaned_data['frompartner'],
                                            topartner=self.cleaned_data['topartner'])
        if blub and (self.instance.pk is None or self.instance.pk != blub[0].id):
            raise django.forms.util.ValidationError(_(u'Combination of fromeditype,frommessagetype,alt,frompartner,topartner already exists.'))
        return self.cleaned_data

class TranslateAdmin(BotsAdmin):
    actions = ('activate',)
    form = MyTranslateAdminForm
    list_display = ('active', 'fromeditype', 'frommessagetype', 'alt', 'frompartner', 'topartner', 'tscript', 'toeditype', 'tomessagetype')
    list_display_links = ('fromeditype',)
    list_filter = ('active','fromeditype','toeditype')
    ordering = ('fromeditype','frommessagetype')
    search_fields = ('fromeditype', 'frommessagetype', 'alt', 'frompartner__idpartner', 'topartner__idpartner', 'tscript', 'toeditype', 'tomessagetype')
    fieldsets = (
        (None,      {'fields': ('active', ('fromeditype', 'frommessagetype'),'tscript', ('toeditype', 'tomessagetype','desc'))
                    }),
        (_(u'Advanced - multiple translations per editype/messagetype'),{'fields': ('alt', 'frompartner', 'topartner'),
                     'classes': ('collapse',)
                    }),
    )
admin.site.register(models.translate,TranslateAdmin)

class UniekAdmin(BotsAdmin):     #AKA counters
    actions = None
    list_display = ('domein', 'nummer')
    list_editable = ('nummer',)
    ordering = ('domein',)
    search_fields = ('domein',)
admin.site.register(models.uniek,UniekAdmin)

#User - change the default display of user screen
UserAdmin.list_display = ('username', 'first_name', 'last_name','email', 'is_active', 'is_staff', 'is_superuser', 'date_joined','last_login')
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

