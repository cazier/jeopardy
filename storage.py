import config

if config.storage == u"dict":
    from stores.storage_dict import *

elif config.storage == u"sqlite":
    from stores.storage_sqlite import *

# pull = storage.pull
# push = storage.push
