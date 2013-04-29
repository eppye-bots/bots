from django.conf import settings
import botsglobal
import models

def set_context(request):
    ''' set variables in the context of templates.
    '''
    bots_environment_text = botsglobal.ini.get('webserver','environment_text',' ')
    bots_environment_text_color = botsglobal.ini.get('webserver','environment_text_color','#000000')
    botslogo = botsglobal.ini.get('webserver','botslogo',"bots/botslogo.html")
    bots_mindate = 0 - botsglobal.ini.getint('settings','maxdays',30)

    try:
        groups = request.user.groups.values_list('name',flat=True)
    except AttributeError:
        groups = None
    if groups and 'touchscreen' in groups:
        bots_touchscreen = True
    else:
        bots_touchscreen = False

    bots_http_path = request.get_full_path()
    if bots_http_path.startswith('/admin/bots/'):
        bots_http_path = bots_http_path[12:]
    else:
        bots_http_path = bots_http_path[1:]
    if bots_http_path:
        if bots_http_path[-1] == '/':
            bots_http_path = bots_http_path[:-1]
    else:
        bots_http_path = 'home'

    #in bots.ini can be indicated that all routes (in config->routes, if route is activated) can be run individually via menu
    if botsglobal.ini.getboolean('webserver','menu_all_routes',False):
        menu_all_routes = list(models.routes.objects.values_list('idroute', flat=True).filter(active=True).order_by('idroute').distinct())
    else:
        menu_all_routes = None

    #in bots.ini it is possible to add custom menu's
    if botsglobal.ini.has_section('custommenus'):
        custom_menuname = botsglobal.ini.get('custommenus','menuname','Custom')
        custom_menus = [(key.title(),value) for key,value in botsglobal.ini.iteritems('custommenus') if key != 'menuname']
    else:
        custom_menuname = None
        custom_menus = None
    
    if hasattr(settings,'DATE_FORMAT_PICKER'):
        DTpicker_date = settings.DATE_FORMAT_PICKER
    else:
        DTpicker_date = 'yy-mm-dd'
    if hasattr(settings,'TIME_FORMAT_PICKER'):
        DTpicker_time = settings.TIME_FORMAT_PICKER
    else:
        DTpicker_time = 'hh:mm:ss'
    DTpicker_ampm = 'true' if 'TT' in DTpicker_time else 'false'


    #the variables in the dict are set. eg in template use {{ bots_environment_text }}
    return {'bots_environment_text':bots_environment_text,
            'bots_environment_text_color':bots_environment_text_color,
            'botslogo':botslogo,
            'bots_minDate':bots_mindate,
            'bots_http_path':bots_http_path,
            'bots_touchscreen':bots_touchscreen,
            'menu_all_routes':menu_all_routes,
            'custom_menus':custom_menus,
            'custom_menuname':custom_menuname,
            'DTpicker_date':DTpicker_date,
            'DTpicker_time':DTpicker_time,
            'DTpicker_ampm':DTpicker_ampm,
            }

