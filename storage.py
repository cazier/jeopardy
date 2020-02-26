import config

if config.storage == u"dict":
    from stores.dict import *

elif config.storage == u"sqlite":
    import stores.sqlite as storage

# pull = storage.pull
# push = storage.push
