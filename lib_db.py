from google.appengine.ext import db
from google.appengine.ext import blobstore
from PIL import Image

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

    width = db.IntegerProperty()
    height = db.IntegerProperty()

    title = db.StringProperty()
    description = db.StringProperty()
    challenge = db.StringProperty()
    permission = db.StringProperty()

    user = db.UserProperty()
    name = db.StringProperty()

    @property
    def size(self):
        """
        Returns the size as a tuple
        """
        reader = blobstore.BlobReader(self.image)
        im = Image.open(reader, 'r')
        s = im.size

        return s # width, height
