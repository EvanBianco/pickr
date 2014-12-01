import webapp2
import hashlib
import StringIO
import time
import cgi

from google.appengine.api import users
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore



# For image manipulation
from PIL import Image

from pickthis import get_result_image, statistics
from constants import local, env, db_parent
from lib_db import ImageObject, Picks, User
from lib_db import Comment

# For image serving
import cloudstorage as gcs

def authenticate(func):
    """
    Wrapper function for methods that require a logged in
    user
    """
    def authenticate_and_call(self, *args, **kwargs):
        user = users.get_current_user()
        if user is None:
            self.redirect('/')
            return
        else:
            return func(self, user.user_id(),*args, **kwargs)
    return authenticate_and_call


def error_catch(func):
    """
    Wrapper for putting all page calls in a try and except
    """
    def call_and_catch(self, *args, **kwargs):

        try:
            func(self, *args, **kwargs)
        except Exception as e:
            print e
            self.redirect("/err")
    return call_and_catch

class ErrorHandler(webapp2.RequestHandler):
    def get(self):
        template = env.get_template("404.html")
        html = template.render()

        self.response.write(html)
        
# Make a basic PageRequest class to handle the params we always need..
class PickThisPageRequest(webapp2.RequestHandler):
    
    def get_base_params(self, **kwargs):

        g_user = users.get_current_user()
        
        if g_user:

            user = User.all().filter("user_id =", g_user.user_id())
            user = user.get()

        
            logout_url = users.create_logout_url('/')
            login_url = None
            email_hash = hashlib.md5(user.email).hexdigest()
            nickname = user.nickname

            cred_points = user.cred()
            admin = users.is_current_user_admin()
        else:
            logout_url = None
            login_url = users.create_login_url('/')
            email_hash = ''
            nickname = None
            cred_points = None
            admin = False

        params = dict(logout_url=logout_url,
                      login_url=login_url,
                      email_hash=email_hash,
                      nickname=nickname,
                      cred_points=cred_points,
                      admin=admin)

        params.update(kwargs)
        return params


class MainPage(webapp2.RequestHandler):

    @error_catch
    def get(self):

        g_user = users.get_current_user()

        if not g_user:
            login_url = users.create_login_url('/')
            template = env.get_template("main.html")
            html = template.render(login_url=login_url,
                                   stats=statistics())
            self.response.out.write(html)

        else:
            logout_url = users.create_logout_url('/')
            login_url = None
            email_hash = hashlib.md5(g_user.email()).hexdigest()

            user_obj = User.all().ancestor(db_parent)
            user_obj = user_obj.filter("user_id =", g_user.user_id())
            user_obj = user_obj.get()

            if not user_obj:
                user_obj = User(user_id=g_user.user_id(),
                                nickname=g_user.nickname(),
                                parent=db_parent,
                                email=g_user.email())
                user_obj.put()
            
            self.redirect('/library')
            

class ResultsHandler(PickThisPageRequest):

    @error_catch
    def get(self):

        user_id = users.get_current_user().user_id()
        image_key = self.request.get("image_key")
        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)
        
        # DO THE MAGIC!
        image = get_result_image(img_obj)

        picks = Picks.all().ancestor(img_obj).fetch(1000)
        pick_users = [p.user_id for p in picks]
        count = len(pick_users)

        owner_user = img_obj.user_id
        
        # Filter out the owner and current user
        if user_id in pick_users: pick_users.remove(user_id) 
        if owner_user in pick_users: pick_users.remove(owner_user) 

        # Get a list of comment strings, if any.
        comments = Comment.all().ancestor(img_obj).order('datetime').fetch(1000)

        params = self.get_base_params(count=count,
                                      image=image,
                                      img_obj=img_obj,
                                      user_id=user_id,
                                      owner_user=owner_user,
                                      pick_users=pick_users, 
                                      comments=comments)

        template = env.get_template("results.html")
        html = template.render(params)

        self.response.write(html)


class AboutHandler(PickThisPageRequest):
    @error_catch
    def get(self):
        template_params = self.get_base_params()
        template = env.get_template('about.html')
        html = template.render(template_params,
                               stats=statistics())
        self.response.write(html)


class TermsHandler(PickThisPageRequest):
    @error_catch
    def get(self):
        template_params = self.get_base_params()
        template = env.get_template('terms.html')
        html = template.render(template_params)
        self.response.write(html)


class PickerHandler(PickThisPageRequest):

    @error_catch
    @authenticate
    def get(self, user_id, id=None):

        if id:
            key_id = id
        else:
            key_id = self.request.get("image_key")


        img_obj= ImageObject.get_by_id(int(key_id),
                                       parent=db_parent)
                
        # Write the page.
        template = env.get_template('pickpoint.html')

        params = self.get_base_params(img_obj=img_obj)
        
        html = template.render(params)


        self.response.write(html)
     
class LibraryHandler(blobstore_handlers.BlobstoreUploadHandler,
                    PickThisPageRequest):

    @error_catch
    def get(self):

        user = users.get_current_user()

        # Unlogged-in people can see the library.
        if user:
            upload_url = blobstore.create_upload_url('/upload')
            user_id = user.user_id()
        else:
            upload_url = ''
            user_id = ''

        # Get the images. 
        # We need to delete images without titles. 
        # I would rather do this in add_image.html
        # but it seems you can't trigger deletion
        # with $(window).on(beforeunload)...
        # https://developer.mozilla.org/en-US/docs/WindowEventHandlers.onbeforeunload
        if users.is_current_user_admin():
            # Then see everything.
            img_objs = ImageObject.all().ancestor(db_parent).fetch(1000)
        else:
            # Then omit aborted uploads.
            img_objs = ImageObject.all().ancestor(db_parent).filter("title !=", '').fetch(1000)

        template = env.get_template('choose.html')

        params = self.get_base_params(img_objs=img_objs,
                                      upload_url=upload_url,
                                      user_id=user_id
                                      )
        html = template.render(params)

        self.response.write(html)

    @error_catch
    def post(self):

        user_id = users.get_current_user().user_id()

        upload_files = self.get_uploads()
        blob_info = upload_files[0]

        # Read the image file
        reader = blobstore.BlobReader(blob_info.key())

        im = Image.open(reader, 'r')

        output = StringIO.StringIO()
        im.save(output, format='PNG')

        bucket = '/pick-this'
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
                             parent=db_parent,
                             user_id=user_id
                             )

        new_db.width = new_db.size[0]
        new_db.height = new_db.size[1]
        
        new_db.put()

        self.redirect('/add_image?image_key=' +
                      str(new_db.id))
        
        
class AddImageHandler(PickThisPageRequest):

    @error_catch
    @authenticate
    def get(self, user_id):

        image_key = self.request.get("image_key")

        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)

        if((user_id == img_obj.user_id) or
           (users.is_current_user_admin())):

            template_params = self.get_base_params()
            template_params.update(img_obj=img_obj,
                                   image_key=image_key)

            template = env.get_template("add_image.html")
            html = template.render(template_params)
            self.response.write(html)

        else:
            raise Exception
            

    @error_catch
    @authenticate
    def post(self, user_id):

        user = User.all().filter("user_id =", user_id).get()
        
        image_key = self.request.get("image_key")

        title = cgi.escape(self.request.get("title"))
        description = cgi.escape(self.request.get("description"))
        challenge = cgi.escape(self.request.get("challenge"))
        pickstyle = self.request.get("pickstyle")
        permission = self.request.get("permission")
        rightsholder1 = cgi.escape(self.request.get("rightsholder1"))
        rightsholder2 = cgi.escape(self.request.get("rightsholder2"))

        # This is pretty gross
        if not rightsholder1:
            if not rightsholder2:
                rightsholder = user.nickname
            else:
                rightsholder = rightsholder2
        else:
            rightsholder = rightsholder1

        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)

        
        if not ((user_id == img_obj.user_id) or
               (users.is_current_user_admin())):
            raise Exception
        

        
        img_obj.width = img_obj.size[0]
        img_obj.height = img_obj.size[1]

        img_obj.title = title.capitalize()
        img_obj.description = description.capitalize()
        img_obj.challenge = challenge.capitalize()
        img_obj.pickstyle = pickstyle
        img_obj.permission = permission
        img_obj.rightsholder = rightsholder
  

        img_obj.put()

        self.redirect('/')
        
