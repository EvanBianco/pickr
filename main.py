import webapp2
from jinja2 import Environment, FileSystemLoader
from os.path import dirname, join
import os
import json
import base64
import hashlib
import StringIO
import time
import numpy as np

from google.appengine.api import users
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore
from google.appengine.api import images

# For image manipulation
from PIL import Image
from pickthis import get_result_image

# For image serving
import cloudstorage as gcs

# Pick This objects
from lib_db import ImageObject, SeismicParent, Picks, Vote

if not os.environ.get('SERVER_SOFTWARE','').startswith('Development'):
    local = False
else:
    local = True

# Jinja2 environment to load templates.
env = Environment(loader=FileSystemLoader(join(dirname(__file__),
                                               'templates')))

# Data store set up.
db_parent = SeismicParent.all().get()
if not db_parent:
    db_parent = SeismicParent()
    db_parent.put()


# Make a basic PageRequest class to handle the params we always need...
class PickThisPageRequest(webapp2.RequestHandler):
    
    def get_base_params(self, **kwargs):

        user = users.get_current_user()
        
        if user:
            logout_url = users.create_logout_url('/')
            login_url = None
            email_hash = hashlib.md5(user.email()).hexdigest()
        else:
            logout_url = None
            login_url = users.create_login_url('/')
            email_hash = ''

        params = dict(logout_url=logout_url,
                      login_url=login_url,
                      email_hash=email_hash)

        return params


class CommentHandler(webapp2.RequestHandler):

    def get(self):

        index = int(self.request.get("index"))

        data = ImageObject.all().ancestor(db_parent).sort("-date")
        data = data.fetch(1000)[index]

        self.response.write(json.dumps(data.comments))

    def post(self):

        index = int(self.request.get("index"))
        comment = int(self.request.get("comment"))

        data = ImageObject.all().ancestor(db_parent).sort("-date")
        data = data.fetch(1000)[index]
        comments = data.comments
        comments.append(comment)

        data.comments = comments
        data.put()

        self.response.write(comment)

      
class VoteHandler(webapp2.RequestHandler):

    def get(self):

        self.response.headers["Content-Type"] = "application/json"
        
        user = users.get_current_user()
        index = int(self.request.get("index"))
        image_key = int(self.request.get("image_key"))

    
        img = ImageObject.get_by_id(image_key, parent=db_parent)
        picks = Picks.all().ancestor(img).order("date").fetch(1000)
        picks = picks[index]

        votes = picks.votes

        if user:
            user_vote = Vote.all().ancestor(picks).filter("user =",
                                                            user)
            user_vote = user_vote.get()
            if not user_vote:
                user_choice = 0
            else:
                user_choice = user_vote.value
                
        else:
            user_choice = 0

        data = {"votes": votes,
                "user_choice": user_choice}
    
        
        self.response.write(json.dumps(data))
        
        
    def post(self):

        self.response.headers["Content-Type"] = "application/json"

        index = int(self.request.get("index"))
        update_vote = int(self.request.get("vote"))
        img_key = int(self.request.get("image_key"))
        user = users.get_current_user()

        img = ImageObject.get_by_id(img_key,
                                    parent=db_parent)
        picks = Picks.all().ancestor(img).order("date").fetch(1000)

        if update_vote > 0:
            update_vote = 1
        else:
            update_vote = -1

        vote = Vote.all().ancestor(picks[index]).filter("user =",
                                                        user).get()
        if vote is None:
            vote = Vote(user=user, value=update_vote,
                        parent=picks[index])
        else:
            vote.value = update_vote

        vote.put()
        
        data = {"votes": picks[index].votes,
                "user_choice": vote.value}
        
        self.response.write(json.dumps(data))
 

class MainPage(webapp2.RequestHandler):
    
    def get(self):

        user = users.get_current_user()

        if not user:
            login_url = users.create_login_url('/')
            template = env.get_template("main.html")
            html = template.render(login_url=login_url)
            self.response.out.write(html)

        else:
            logout_url = users.create_logout_url('/')
            login_url = None
            email_hash = hashlib.md5(user.email()).hexdigest()
            self.redirect('/library')
            

class ResultsHandler(webapp2.RequestHandler):
    def get(self):

        image_key = self.request.get("image_key")
        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)
        image_url = images.get_serving_url(img_obj.image)

        image, count = get_result_image(img_obj)
        image_width = img_obj.width
        image_height = img_obj.height

        user = users.get_current_user()

        # User should exist, so this should fail otherwise.
        logout_url = users.create_logout_url('/')
        login_url = None
        email_hash = hashlib.md5(user.email()).hexdigest()

        template = env.get_template("results.html")
        html = template.render(count=count,
                                logout_url=logout_url,
                                email_hash=email_hash,
                                image=image,
                                image_url=image_url,
                                image_key=image_key,
                                image_width=image_width,
                                image_height=image_height)

        self.response.write(html)


class AboutHandler(PickThisPageRequest):
    def get(self):
        template_params = self.get_base_params()
        template = env.get_template('about.html')
        html = template.render(template_params)
        self.response.write(html)


class TermsHandler(PickThisPageRequest):
    def get(self):
        template_params = self.get_base_params()
        template = env.get_template('terms.html')
        html = template.render(template_params)
        self.response.write(html)


class PickerHandler(webapp2.RequestHandler):

    def get(self, id=None):

        user = users.get_current_user()

        # User should exist, so this should fail otherwise.
        logout_url = users.create_logout_url('/')
        login_url = None
        email_hash = hashlib.md5(user.email()).hexdigest()

        if id:
            key_id = id
        else:
            key_id = self.request.get("image_key")


        img_obj= ImageObject.get_by_id(int(key_id),
                                       parent=db_parent)

        try:
            image_url = images.get_serving_url(img_obj.image)
        except:
            print "handle this error"
                
        challenge = img_obj.challenge
        permission = img_obj.permission
        image_width = img_obj.width
        image_height = img_obj.height

        # Write the page.
        template = env.get_template('pickpoint.html')
        html = template.render(logout_url=logout_url,
                               login_url=login_url,
                               email_hash=email_hash,
                               image_url=image_url,
                               image_key=key_id,
                               challenge=challenge,
                               permission=permission,
                               image_width=image_width,
                               image_height=image_height)

        self.response.write(html)
     

class PickHandler(webapp2.RequestHandler):

    def get(self):

        user = users.get_current_user()
        image_key = self.request.get("image_key")
        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)

        if self.request.get("user_picks"):
   
            seismic_obj = Picks.all().ancestor(img_obj)
            data = seismic_obj.filter("user =", user).get()
            
            if data:
                picks = data.picks
            else:
                picks = json.dumps([])
            self.response.write(picks)
            return
        
        if self.request.get("all"):
            data = Picks.all().ancestor(img_obj).fetch(1000)

            picks = [i.picks for i in data]
            self.response.write(data)
            return

        if self.request.get("pick_index"):

            data = Picks.all().ancestor(img_obj)
            data = data.order("-date").fetch(1000)

            index = int(self.request.get("pick_index"))

            self.response.write(data[index].picks)
            return

    def post(self):

        point = (int(self.request.get("x")),
                 int(self.request.get("y")))

        user = users.get_current_user()
        image_key = self.request.get("image_key")

        if not user:
            self.redirect('/')

        image_obj = ImageObject.get_by_id(int(image_key),
                                          parent=db_parent)
        picks = Picks.all().ancestor(image_obj)
        picks = picks.filter("user =", user).get()

        if not picks:
            picks = Picks(user=user,
                          picks=json.dumps([point]).encode(),
                          parent=image_obj)
            picks.put()
        else:

            all_picks = json.loads(picks.picks)
            all_picks.append(point)
            picks.picks = json.dumps(all_picks).encode()
            picks.put()
            
        self.response.write("Ok")


    def delete(self):

        user = users.get_current_user()
        image_key = self.request.get("image_key")

        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)

        data = Picks.all().ancestor(img_obj).filter("user =",
                                                           user)
        data = data.get()

        points = json.loads(data.picks)

        if self.request.get("clear"):
            data.delete()
            value = []
            
        elif self.request.get("undo"):
            
            value = points.pop()
            data.picks = json.dumps(points).encode()
            data.put()
                 
        self.response.write(json.dumps(value))


class LibraryHandler(blobstore_handlers.BlobstoreUploadHandler,
                    webapp2.RequestHandler):

    def get(self):

        user = users.get_current_user()
        
        if user:
            logout_url = users.create_logout_url('/')
            login_url = None
            email_hash = hashlib.md5(user.email()).hexdigest()
        else:
            logout_url = None
            login_url = users.create_login_url('/')
            email_hash = ''

        upload_url = blobstore.create_upload_url('/upload')

        # Get the thumbnail urls
        img_obj = ImageObject.all().ancestor(db_parent).fetch(1000)

        image_dict = [{"key": i.key().id(),
                       "title": i.title,
                       "description": i.description,
                       "challenge": i.challenge,
                       "permission": i.permission,
                       "image": images.get_serving_url(i.image)}
                       for i in img_obj]

        template = env.get_template('choose.html')
        html = template.render(images=image_dict,
                               upload_url=upload_url,
                               logout_url=logout_url,
                               login_url=login_url,
                               email_hash=email_hash)

        self.response.write(html)

    def post(self):

        user = users.get_current_user()


        upload_files = self.get_uploads()
        blob_info = upload_files[0]

        # Read the image file
        reader = blobstore.BlobReader(blob_info.key())

        im = Image.open(reader, 'r')

        output = StringIO.StringIO()
        im.save(output, format='PNG')

        bucket = '/pickr_bucket/'
        output_filename = (bucket +'/2' + str(time.time()))

        gcsfile = gcs.open(output_filename, 'w')
        gcsfile.write(output.getvalue())

        output.close()
        gcsfile.close()

        # Make a blob reference
        bs_file = '/gs' + output_filename
        output_blob_key = blobstore.create_gs_key(bs_file)

        name = self.request.get("name")
        description = self.request.get("description")

        new_db = ImageObject(description=description,
                             image=output_blob_key,
                             parent=db_parent)

        new_db.put()

        self.redirect('/add_image?image_key=' +
                      str(new_db.key().id())) 
        
        
class AddImageHandler(PickThisPageRequest):

    def get(self):

        image_key = self.request.get("image_key")

        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)

        image_url = images.get_serving_url(img_obj.image)

        
        template_params = self.get_base_params()
        template_params.update(image_url=image_url,
                               image_key=image_key)

        template = env.get_template("add_image.html")
        html = template.render(template_params)
        self.response.write(html)

    def post(self):

        user = users.get_current_user()
        image_key = self.request.get("image_key")

        title = self.request.get("title")
        description = self.request.get("description")
        challenge = self.request.get("challenge")
        pickstyle = self.request.get("pickstyle")
        permission = self.request.get("permission")

        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)

        img_obj.width = img_obj.size[0]
        img_obj.height = img_obj.size[1]

        img_obj.title = title
        img_obj.description = description
        img_obj.challenge = challenge
        img_obj.pickstyle = pickstyle
        img_obj.permission = permission

        img_obj.put()

        self.redirect('/')


# This is the app.  
app = webapp2.WSGIApplication([
    ('/', MainPage),
    (r'/([0-9]+)$', PickerHandler),
    ('/upload', LibraryHandler),
    ('/library', LibraryHandler),
    ('/add_image', AddImageHandler),
    ('/about', AboutHandler),
    ('/update_pick', PickHandler),
    ('/pickr', PickerHandler),
    ('/terms', TermsHandler),
    ('/results', ResultsHandler),
    ('/comment', CommentHandler),
    ('/vote', VoteHandler)],
    debug=True)
