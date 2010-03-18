import django
from django.contrib import admin
#***********
import models
import botsglobal

screen_limit = botsglobal.ini.getint('settings','limit',30)
#~ screen_limit = 30

def activate(ding, request, queryset):
    ''' admin action for several models.'''
    for obj in queryset:
        obj.active = not obj.active
        obj.save()
activate.short_description = "Toggle active"

#*****************************************************************************************************
class CcodeAdmin(admin.ModelAdmin):
    list_display = ('ccodeid','leftcode','rightcode','attr1','attr2','attr3','attr4','attr5','attr6','attr7','attr8')
    list_display_links = ('ccodeid',)
    list_filter = ('ccodeid',)
    list_per_page = screen_limit
    ordering = ('ccodeid','leftcode')
admin.site.register(models.ccode,CcodeAdmin)

class CcodeInline(admin.TabularInline):
    model = models.ccode
    extra = 1
    ordering = ('leftcode',)

class CcodetriggerAdmin(admin.ModelAdmin):
    list_display = ('ccodeid',)
    list_display_links = ('ccodeid',)
    list_per_page = screen_limit
    inlines = (CcodeInline,)
admin.site.register(models.ccodetrigger,CcodetriggerAdmin)

class ChannelAdmin(admin.ModelAdmin):
    list_display = ('idchannel', 'inorout', 'type','host', 'port', 'username', 'secret', 'path', 'filename',  'remove', 'archivepath', 'charset')
    list_filter = ('inorout','type')
    list_per_page = screen_limit
    ordering = ('idchannel',)
    save_as = True
    fieldsets = (
        (None,          {'fields': ('idchannel', ('inorout','type'), ('host','port'), ('username'), ('path', 'filename'), 'remove', 'archivepath', 'charset')
                        }),
        ('FTP specific data',{'fields': ('ftpactive', 'ftpbinary', 'ftpaccount' ),
                         'classes': ('collapse',)
                        }),
        ('Advanced',{'fields': (('lockname', 'syslock'), 'parameters', 'starttls'),
                         'classes': ('collapse',)
                        }),
    )
admin.site.register(models.channel,ChannelAdmin)

class ConfirmruleAdmin(admin.ModelAdmin):
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

class MyTranslateAdminForm(django.forms.ModelForm):
    ''' customs form for translations to check if entry exitsts (unique_together not validated right (because of null values in partner fields))'''
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
                raise django.forms.util.ValidationError('This combination of fromeditype,frommessagetype,alt,frompartner,topartner already exists!')
        return self.cleaned_data

class PartnerAdmin(admin.ModelAdmin):
    list_display = ('active','idpartner')   #is needed for list_display_links, but not used.
    list_display_links = ('idpartner',)
    list_filter = ('active',)
    list_per_page = screen_limit
    actions = (activate,)
    def queryset(self, request):
        qs = super(PartnerAdmin, self).queryset(request)
        qs = qs.filter(isgroup=self.isgroup)
        return qs
    def save_model(self, request, obj, form, change):
        obj.isgroup = self.isgroup
        obj.save()
admin.site.register(models.partner,PartnerAdmin)

class EdiGroupAdmin(PartnerAdmin):
    list_display = ('active','idpartner', 'name')
    #~ list_display_links = ('idpartner',)
    fields = ('active', 'idpartner', 'name')
    isgroup = True
admin.site.register(models.edigroup,EdiGroupAdmin)

class EdiPartnerAdmin(PartnerAdmin):
    list_display = ('active','idpartner', 'name','mail','cc')
    fields = ('active', 'idpartner', 'name','mail','cc','group')
    filter_horizontal = ('group',)
    inlines = (MailInline,)
    isgroup = False
admin.site.register(models.edipartner,EdiPartnerAdmin)

class RoutesAdmin(admin.ModelAdmin):
    list_display = ('active', 'idroute', 'seq', 'fromchannel', 'fromeditype', 'frommessagetype', 'alt', 'frompartner', 'topartner', 'translateind', 'tochannel', 'toeditype', 'tomessagetype', 'frompartner_tochannel', 'topartner_tochannel', 'testindicator')
    list_display_links = ('idroute',)
    list_filter = ('active','fromeditype','testindicator')
    ordering = ('idroute','seq')
    actions = (activate,)
    list_per_page = screen_limit
    fieldsets = (
        (None,      {'fields':  ('active',('idroute', 'seq'),'fromchannel', ('fromeditype', 'frommessagetype'))
                    }),
        ('Advanced - multiple translations for one messagetype, eg partner specific translation',{'fields':  ('alt', 'frompartner', 'topartner'),
                     'classes': ('collapse',) 
                    }),
        (None,      {'fields':  ('translateind','tochannel')}),
        ('Advanced - filter edi messages for outchannel',{'fields':(('toeditype', 'tomessagetype'),'frompartner_tochannel', 'topartner_tochannel', 'testindicator'),
                    'classes':  ('collapse',)
                    }),
    )
admin.site.register(models.routes,RoutesAdmin)

class TranslateAdmin(admin.ModelAdmin):
    form = MyTranslateAdminForm
    list_display = ('active', 'fromeditype', 'frommessagetype', 'alt', 'frompartner', 'topartner', 'tscript', 'toeditype', 'tomessagetype')
    list_display_links = ('fromeditype',)
    list_filter = ('active','fromeditype','toeditype')
    actions = (activate,)
    list_per_page = screen_limit
    fieldsets = (
        (None,      {'fields': ('active', ('fromeditype', 'frommessagetype'))
                    }),
        ('Advanced - multiple translations for one messagetype, eg partner specific translation',{'fields': ('alt', 'frompartner', 'topartner'),
                     'classes': ('collapse',)
                    }),
        (None,      {'fields': ('tscript', ('toeditype', 'tomessagetype'))
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

