from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.api import images
from google.appengine.api import users

from PIL import Image


import json


class User(db.Model):

    # Hack to log the number of users who have logged in
    user_id = db.StringProperty()
    nickname = db.StringProperty()
    email = db.EmailProperty()
    
    def cred(self):

        all_picks = Picks.all().filter("user_id =",
                                       self.user_id).fetch(1000)
        all_imgs  = \
          ImageObject.all().filter("user_id =",
                                    self.user_id).filter("title !=",
                                                      '').fetch(1000)

        

        rep = 1 # everyone start with 1

        # Award rep for votes received.
        for picks in all_picks:
            rep += picks.votes

        # Award rep for interpretations made.
        rep += 3 * len(all_picks)

        # Award rep for uploading.
        rep += 3 * len(all_imgs)

        return rep + 20

class Vote(db.Model):

    # The user_id of the vote caster
    user_id = db.StringProperty()

    # +1 or -1
    value = db.IntegerProperty()
    
class ImageParent(db.Model):
    pass

class Challenge(db.Model):
    pass
    
    # ImageObject as parent

    # Inherited? user_id = db.StringProperty()
    
    # Consists of several pick objects
    
    # Could have time taken for total interpretation
    # Could have overall challenge text
    
    # Maybe this doesn't need to exist, just 
    # use PickObjects directly. 
    
    
class PickObject(db.Model):
    pass

    # Challenge as parent
    # Inherits user_id
    
    #colour = db.StringProperty()
    #style = db.StringProperty() # dotted, small, large

    # What are you actually asking people
    # to pick? 
    #challenge = db.StringProperty()
    
    # This is in ImageObject now
    #pickstyle = db.StringProperty()
    
    # Points and text 
    # Maybe they just interpret the image
    # And maybe we add the hint based
    # on their interpretation.
    # Not sure what property this would be...
    #hint = db.StringProperty()
    
    # Now Picks() will be a child of this.
    

class Picks(db.Model):

    user_id = db.StringProperty()
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
        

class Comment(db.Model):

    # Parent should be ImageObject

    text = db.TextProperty(required=True)
    user_id = db.StringProperty()
    datetime = db.DateTimeProperty(auto_now_add=True)

    @property
    def nickname(self):

        user = User.all().filter("user_id =",
                                 self.user_id).get()
        return user.nickname
    

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

    favouriters = db.ListProperty(str, default=[])

    # This is safer than using a user directly
    # Because email address can change.
    user_id = db.StringProperty()

    @property
    def interpreters(self):
        """
        Returns a list of user_ids that have
        interpreted this image.
        """
        picks = Picks.all().ancestor(self)
        user_ids = [p.user_id for p in picks]

        return user_ids

    @property
    def size(self):
        """
        Returns the size as a tuple
        """
        reader = blobstore.BlobReader(self.image)
        im = Image.open(reader, 'r')
        s = im.size

        return s # width, height

    # I think this has to be a method, not property,
    # if we want to pass in arguments.
    def url(self, size=0, crop=False):
        """
        Returns a serving url for the image
        """
        return images.get_serving_url(self.image,
                                      size=size,
                                      crop=crop)

    @property
    def id(self):

        return self.key().id()
    

    @property
    def nickname(self):

        user = User.all().filter("user_id =",
                                 self.user_id).get()
        return user.nickname
    
        
