from bots import botsglobal
import models

def set_context(request):
    ''' set variables in the context of templates.
    '''
    bots_environment_text = botsglobal.ini.get('webserver','environment_text',' ')
    botslogo = botsglobal.ini.get('webserver','botslogo',"bots/botslogo.html")
    bots_minDate = 0 - botsglobal.ini.getint('settings','maxdays',30)

    groups = request.user.groups.values_list('name',flat=True)
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
    
    #in bots.ini it is possible to indicate that all routes (in config->routes) can be run individually via menu
    # Run individual routes from the run menu if enabled
    menu_all_routes = []
    if botsglobal.ini.getboolean('webserver','menu_all_routes',False):
        for route in models.routes.objects.values_list('idroute', flat=True).filter(active=True).order_by('idroute').distinct():
            menu_all_routes.append(route)
    
    #in bots.ini it is possible to add custom menu's
    custom_menus = {}
    for key, value in botsglobal.ini.items('custommenus'):
        custom_menus[key] = value

    #the variables in the dict are set. eg in template use {{ bots_environment_text }}
    return {'bots_environment_text':bots_environment_text, 
            'botslogo':botslogo, 
            'bots_minDate':bots_minDate,
            'bots_http_path':bots_http_path, 
            'bots_touchscreen':bots_touchscreen, 
            'menu_all_routes':menu_all_routes,
            'custom_menus':custom_menus,
            }

