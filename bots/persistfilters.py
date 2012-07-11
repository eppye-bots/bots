# code found at code.djangoproject.com/ticket/3777
from django import http


class FilterPersistMiddleware(object):

    def _get_default(self, key):
        # Gets any set default filters for the admin. Returns None if no default is set.
        default = None
        #~ default = settings.ADMIN_DEFAULT_FILTERS.get(key, None)
        # Filters are allowed to be functions. If this key is one, call it.
        if hasattr(default, '__call__'):
            default = default()
        return default

    def process_request(self, request):
        if '/admin/' not in request.path or request.method == 'POST':
            return None

        if request.META.has_key('HTTP_REFERER'):
            referrer = request.META['HTTP_REFERER'].split('?')[0]
            referrer = referrer[referrer.find('/admin'):len(referrer)]
        else:
            referrer = u''

        popup = 'pop=1' in request.META['QUERY_STRING']
        path = request.path
        query_string = request.META['QUERY_STRING']
        session = request.session

        if session.get('redirected', False):  #so that we dont loop once redirected
            del session['redirected']
            return None

        key = 'key'+path.replace('/','_')
        if popup:
            key = 'popup'+key

        if path == referrer:
            # We are in the same page as before. We assume that filters were changed and update them.
            if query_string == '':     #Filter is empty, delete it
                if session.has_key(key):
                    del session[key]
                return None
            else:
                request.session[key] = query_string
        else:
            # We are are coming from another page. Set querystring to saved or default value.
            query_string = session.get(key, self._get_default(key))
            if query_string is not None:
                redirect_to = path + '?' + query_string
                request.session['redirected'] = True
                return http.HttpResponseRedirect(redirect_to)
            else:
                return None

#~ Sample default filters:
#~
#~ from datetime import date
#~ def _today():
    #~ return 'starttime__gte=' + date.today().isoformat()
#~
#~ # Default filters. Format: 'key_$url', where $url has slashes replaced
#~ # with underscores
#~ # value can either be a function or a string
#~ ADMIN_DEFAULT_FILTERS= {
    #~ # display only events starting today
    #~ 'key_admin_event_calendar_event_': _today,
    #~ # display active members
    #~ 'key_admin_users_member_': 'is_active__exact=1',
    #~ # only show new suggestions
    #~ 'key_admin_suggestions_suggestion_': 'status__exact=new',
#~ }
