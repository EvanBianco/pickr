from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.api import images

from PIL import Image


import json


class Vote(db.Model):

    user = db.UserProperty()
    value = db.IntegerProperty()
    
class ImageParent(db.Model):
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

    title = db.StringProperty(default="")
    description = db.StringProperty(default="")
    challenge = db.StringProperty(default="")
    permission = db.StringProperty(default="")
    pickstyle = db.StringProperty(default="")
    rightsholder = db.StringProperty(default="")

    # This is safer than using a user directly
    # Because email address can change.
    user_id = db.StringProperty()

    # Not sure if we need this for backwards compatibility?
    user = db.UserProperty()

    name = db.StringProperty() # What is this for? 
                               # Doesn't get populated.

    interpreters = db.ListProperty(str, default=[])
    favouriters = db.ListProperty(str, default=[])

    @property
    def size(self):
        """
        Returns the size as a tuple
        """
        reader = blobstore.BlobReader(self.image)
        im = Image.open(reader, 'r')
        s = im.size

        return s # width, height

    @property
    def url(self):
        """
        Returns a serving url for the image
        """
        return images.get_serving_url(self.image)

    @property
    def id(self):

        return self.key().id()
    
