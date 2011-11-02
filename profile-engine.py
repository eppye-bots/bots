#!/usr/bin/env python

if __name__ == '__main__':
    import cProfile
    cProfile.run('from bots import engine; engine.start()','profile.tmp')
    import pstats
    p = pstats.Stats('profile.tmp')
    #~ p.sort_stats('cumulative').print_stats(25)
    p.sort_stats('time').print_stats(25)
    #~ p.print_callees('deepcopy').print_stats(1)
    p.sort_stats('time').print_stats('grammar.py',50)

        
