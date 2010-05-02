import django
from django.contrib import admin
from django.utils.translation import ugettext as _
#***********
import models
import botsglobal

screen_limit = botsglobal.ini.getint('settings','limit',30)

def activate(ding, request, queryset):
    ''' admin action for several models.'''
    for obj in queryset:
        obj.active = not obj.active
        obj.save()
activate.short_description = _(u'(de)activate')

#*****************************************************************************************************
class CcodeAdmin(admin.ModelAdmin):
    list_display = ('ccodeid','leftcode','rightcode','attr1','attr2','attr3','attr4','attr5','attr6','attr7','attr8')
    list_display_links = ('ccodeid',)
    list_filter = ('ccodeid',)
    list_per_page = screen_limit
    ordering = ('ccodeid','leftcode')
admin.site.register(models.ccode,CcodeAdmin)

#~ class CcodeInline(admin.TabularInline):
    #~ model = models.ccode
    #~ extra = 1
    #~ ordering = ('leftcode',)

class CcodetriggerAdmin(admin.ModelAdmin):
    list_display = ('ccodeid','ccodeid_desc',)
    list_display_links = ('ccodeid',)
    list_per_page = screen_limit
    #~ inlines = (CcodeInline,)
admin.site.register(models.ccodetrigger,CcodetriggerAdmin)

class ChannelAdmin(admin.ModelAdmin):
    list_display = ('idchannel', 'inorout', 'type','host', 'port', 'username', 'secret', 'path', 'filename',  'remove', 'archivepath', 'charset')
    list_filter = ('inorout','type')
    list_per_page = screen_limit
    ordering = ('idchannel',)
    fieldsets = (
        (None,          {'fields': ('idchannel', ('inorout','type'), ('host','port'), ('username', 'secret'), ('path', 'filename'), 'remove', 'archivepath', 'charset','desc')
                        }),
        (_(u'FTP specific data'),{'fields': ('ftpactive', 'ftpbinary', 'ftpaccount' ),
                         'classes': ('collapse',)
                        }),
        (_(u'Advanced'),{'fields': (('lockname', 'syslock'), 'parameters', 'starttls'),
                         'classes': ('collapse',)
                        }),
    )
admin.site.register(models.channel,ChannelAdmin)

class ConfirmruleAdmin(admin.ModelAdmin):
    save_as = True
    list_display = ('active','negativerule','confirmtype','ruletype', 'frompartner', 'topartner','idroute','idchannel','editype','messagetype')
    list_display_links = ('confirmtype',)
    list_filter = ('active','confirmtype','ruletype')
    list_per_page = screen_limit
    actions = (activate,)
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

class PartnerAdmin(admin.ModelAdmin):
    form = MyPartnerAdminForm
    inlines = (MailInline,)
    fields = ('active', 'isgroup', 'idpartner', 'name','mail','cc','group')
    list_display = ('active','isgroup','idpartner', 'name','mail','cc')
    list_display_links = ('idpartner',)
    list_filter = ('active','isgroup')
    filter_horizontal = ('group',)
    list_per_page = screen_limit
    actions = (activate,)
admin.site.register(models.partner,PartnerAdmin)

class RoutesAdmin(admin.ModelAdmin):
    save_as = True
    list_display = ('active', 'idroute', 'seq', 'fromchannel', 'fromeditype', 'frommessagetype', 'alt', 'frompartner', 'topartner', 'translateind', 'tochannel', 'toeditype', 'tomessagetype', 'frompartner_tochannel', 'topartner_tochannel', 'testindicator', 'notindefaultrun')
    list_display_links = ('idroute',)
    list_filter = ('active','fromeditype','testindicator')
    ordering = ('idroute','seq')
    actions = (activate,)
    list_per_page = screen_limit
    fieldsets = (
        (None,      {'fields':  ('active',('idroute', 'seq'),'fromchannel', ('fromeditype', 'frommessagetype'),'translateind','tochannel','desc')}),
        (_(u'Filtering for outchannel'),{'fields':('toeditype', 'tomessagetype','frompartner_tochannel', 'topartner_tochannel', 'testindicator'),
                    'classes':  ('collapse',)
                    }),
        (_(u'Advanced'),{'fields':  ('alt', 'frompartner', 'topartner', 'notindefaultrun'),
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
        b = models.translate.objects.filter(fromeditype=self.cleaned_data['fromeditype'],
                                            frommessagetype=self.cleaned_data['frommessagetype'],
                                            alt=self.cleaned_data['alt'],
                                            frompartner=self.cleaned_data['frompartner'],
                                            topartner=self.cleaned_data['topartner'])
        if b and (self.instance.pk is None or self.instance.pk != b[0].id):
            raise django.forms.util.ValidationError(_(u'Combination of fromeditype,frommessagetype,alt,frompartner,topartner already exists.'))
        return self.cleaned_data

class TranslateAdmin(admin.ModelAdmin):
    form = MyTranslateAdminForm
    save_as = True
    list_display = ('active', 'fromeditype', 'frommessagetype', 'alt', 'frompartner', 'topartner', 'tscript', 'toeditype', 'tomessagetype')
    list_display_links = ('fromeditype',)
    list_filter = ('active','fromeditype','toeditype')
    actions = (activate,)
    list_per_page = screen_limit
    fieldsets = (
        (None,      {'fields': ('active', ('fromeditype', 'frommessagetype'),'tscript', ('toeditype', 'tomessagetype','desc'))
                    }),
        (_(u'Advanced - multiple translations per editype/messagetype'),{'fields': ('alt', 'frompartner', 'topartner'),
                     'classes': ('collapse',)
                    }),
    )
admin.site.register(models.translate,TranslateAdmin)

class UniekAdmin(admin.ModelAdmin):     #AKA counters
    list_display = ('domein', 'nummer')
    list_editable = ('nummer',)
    list_per_page = screen_limit
    ordering = ('domein',)
    actions = None
admin.site.register(models.uniek,UniekAdmin)

#User - change the default display of user screen
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
UserAdmin.list_display = ('username', 'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login')
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

