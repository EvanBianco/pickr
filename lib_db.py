from google.appengine.ext import db
from google.appengine.ext import blobstore

import json


class Vote(db.Model):

    user = db.UserProperty()
    value = db.IntegerProperty()
    
class SeismicParent(db.Model):
    pass

class Picks(db.Model):

    user = db.UserProperty()
    comments = db.StringListProperty()
    date = db.DateTimeProperty(auto_now_add=True)
    picks = db.BlobProperty()

    @property
    def votes(self):
        """
        Returns the vote count for the picks
        """
        votes = Vote.all().ancestor(self).fetch(10000)

        total = 0
        for vote in votes:
            total += vote.value

        return total
        
    
class ImageObject(db.Model):

    image = blobstore.BlobReferenceProperty()
    description = db.StringProperty()

    challenge = db.StringProperty()
    title = db.StringProperty()
    permission = db.StringProperty()

    user = db.UserProperty()
    name = db.StringProperty()
   




