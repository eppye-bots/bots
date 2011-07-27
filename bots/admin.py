import django
from django.contrib import admin
from django.utils.translation import ugettext as _
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.contrib.admin.util import unquote, flatten_fieldsets, get_deleted_objects, model_ngettext, model_format_dict
from django.core.exceptions import PermissionDenied
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import capfirst, get_text_list
#***********
import models
import botsglobal

admin.site.disable_action('delete_selected')


class BotsAdmin(admin.ModelAdmin):
    list_per_page = botsglobal.ini.getint('settings','limit',30)
    save_as = True

    def delete_view(self, request, object_id, extra_context=None):
        ''' copy from admin.ModelAdmin; adapted: do not checkl references: no cascading deletes; no confirmation.'''
        opts = self.model._meta
        app_label = opts.app_label
        try:
            obj = self.queryset(request).get(pk=unquote(object_id))
        except self.model.DoesNotExist:
            obj = None
        if not self.has_delete_permission(request, obj):
            raise PermissionDenied
        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})
        obj_display = force_unicode(obj)
        self.log_deletion(request, obj, obj_display)
        obj.delete()

        self.message_user(request, _('The %(name)s "%(obj)s" was deleted successfully.') % {'name': force_unicode(opts.verbose_name), 'obj': force_unicode(obj_display)})

        if not self.has_change_permission(request, None):
            return HttpResponseRedirect("../../../../")
        return HttpResponseRedirect("../../")
    def activate(self, request, queryset):
        ''' admin action.'''
        for obj in queryset:
            obj.active = not obj.active
            obj.save()
    activate.short_description = _(u'activate/de-activate')
    def bulk_delete(self, request, queryset):
        ''' admin action.'''
        for obj in queryset:
            obj.delete()
    bulk_delete.short_description = _(u'delete selected')

#*****************************************************************************************************
class CcodeAdmin(BotsAdmin):
    list_display = ('ccodeid','leftcode','rightcode','attr1','attr2','attr3','attr4','attr5','attr6','attr7','attr8')
    list_display_links = ('ccodeid',)
    list_filter = ('ccodeid',)
    #~ ordering = ('ccodeid','leftcode')
    actions = ('bulk_delete',)
    search_fields = ('leftcode','rightcode','attr1','attr2','attr3','attr4','attr5','attr6','attr7','attr8')
    def lookup_allowed(self, lookup, *args, **kwargs):
        if lookup.startswith('ccodeid'):
            return True
        return super(CcodeAdmin, self).lookup_allowed(lookup, *args, **kwargs)
admin.site.register(models.ccode,CcodeAdmin)

class CcodetriggerAdmin(BotsAdmin):
    list_display = ('ccodeid','ccodeid_desc',)
    list_display_links = ('ccodeid',)
    actions = ('bulk_delete',)
admin.site.register(models.ccodetrigger,CcodetriggerAdmin)

class ChannelAdmin(BotsAdmin):
    list_display = ('idchannel', 'inorout', 'type','host', 'port', 'username', 'secret', 'path', 'filename',  'remove', 'archivepath', 'charset')
    list_filter = ('inorout','type')
    #~ ordering = ('idchannel',)
    actions = ('bulk_delete',)
    fieldsets = (
        (None,          {'fields': ('idchannel', ('inorout','type'), ('host','port'), ('username', 'secret'), ('path', 'filename'), 'remove', 'archivepath', 'charset','desc')
                        }),
        (_(u'FTP specific data'),{'fields': ('ftpactive', 'ftpbinary', 'ftpaccount' ),
                         'classes': ('collapse',)
                        }),
        (_(u'Advanced'),{'fields': (('lockname', 'syslock'), 'parameters', 'starttls','apop','askmdn'),
                         'classes': ('collapse',)
                        }),
    )
admin.site.register(models.channel,ChannelAdmin)

class ConfirmruleAdmin(BotsAdmin):
    list_display = ('active','negativerule','confirmtype','ruletype', 'frompartner', 'topartner','idroute','idchannel','editype','messagetype')
    list_display_links = ('confirmtype',)
    list_filter = ('active','confirmtype','ruletype')
    actions = ('activate','bulk_delete')
    #~ ordering = ('confirmtype','ruletype')
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
    form = MyPartnerAdminForm
    inlines = (MailInline,)
    fields = ('active', 'isgroup', 'idpartner', 'name','mail','cc','group')
    list_display = ('active','isgroup','idpartner', 'name','mail','cc')
    list_display_links = ('idpartner',)
    list_filter = ('active','isgroup')
    filter_horizontal = ('group',)
    actions = ('bulk_delete','activate')
    search_fields = ('idpartner','name')
admin.site.register(models.partner,PartnerAdmin)

class RoutesAdmin(BotsAdmin):
    list_display = ('active', 'idroute', 'seq', 'fromchannel', 'fromeditype', 'frommessagetype', 'alt', 'frompartner', 'topartner', 'translateind', 'tochannel', 'defer', 'toeditype', 'tomessagetype', 'frompartner_tochannel', 'topartner_tochannel', 'testindicator', 'notindefaultrun')
    list_display_links = ('idroute',)
    list_filter = ('idroute','active','fromeditype','testindicator')
    actions = ('bulk_delete','activate')
    fieldsets = (
        (None,      {'fields':  ('active',('idroute', 'seq'),'fromchannel', ('fromeditype', 'frommessagetype'),'translateind','tochannel','desc')}),
        (_(u'Filtering for outchannel'),{'fields':('toeditype', 'tomessagetype','frompartner_tochannel', 'topartner_tochannel', 'testindicator'),
                    'classes':  ('collapse',)
                    }),
        (_(u'Advanced'),{'fields':  ('alt', 'frompartner', 'topartner', 'notindefaultrun','defer'),
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

class TranslateAdmin(BotsAdmin):
    form = MyTranslateAdminForm
    list_display = ('active', 'fromeditype', 'frommessagetype', 'alt', 'frompartner', 'topartner', 'tscript', 'toeditype', 'tomessagetype')
    list_display_links = ('fromeditype',)
    list_filter = ('active','fromeditype','toeditype')
    actions = ('bulk_delete','activate')
    fieldsets = (
        (None,      {'fields': ('active', ('fromeditype', 'frommessagetype'),'tscript', ('toeditype', 'tomessagetype','desc'))
                    }),
        (_(u'Advanced - multiple translations per editype/messagetype'),{'fields': ('alt', 'frompartner', 'topartner'),
                     'classes': ('collapse',)
                    }),
    )
admin.site.register(models.translate,TranslateAdmin)

class UniekAdmin(BotsAdmin):     #AKA counters
    list_display = ('domein', 'nummer')
    list_editable = ('nummer',)
    #~ ordering = ('domein',)
    actions = None
admin.site.register(models.uniek,UniekAdmin)

#User - change the default display of user screen
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
UserAdmin.list_display = ('username', 'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login')
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

