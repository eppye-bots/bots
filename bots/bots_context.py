from bots import botsglobal

def set_context(request):
    ''' set variables in the context of templates.
    '''
    bots_environment_text = botsglobal.ini.get('webserver','environment_text',' ')
    botslogo = botsglobal.ini.get('webserver','botslogo',"bots/botslogo.html")
    bots_minDate = 0 - botsglobal.ini.getint('settings','maxdays',30)

    if 'touchscreen' in request.user.groups.all():
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
        
    #the variables in the dict are set. eg in template use {{ bots_environment_text }}
    return {'bots_environment_text':bots_environment_text, 'botslogo':botslogo, 'bots_minDate':bots_minDate, 'bots_http_path':bots_http_path, 'bots_touchscreen':bots_touchscreen}

