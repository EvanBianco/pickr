import webapp2
import hashlib
import StringIO
import time

from google.appengine.api import users
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore



# For image manipulation
from PIL import Image

from pickthis import get_result_image, get_cred
from constants import local, env, db_parent
from lib_db import ImageObject

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
            return func(self, user,*args, **kwargs)
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
        
# Make a basic PageRequest class to handle the params we always need...
class PickThisPageRequest(webapp2.RequestHandler):
    
    def get_base_params(self, **kwargs):

        user = users.get_current_user()
        
        if user:
            logout_url = users.create_logout_url('/')
            login_url = None
            email_hash = hashlib.md5(user.email()).hexdigest()
            nickname = user.nickname()
            cred_points = get_cred(user)
        else:
            logout_url = None
            login_url = users.create_login_url('/')
            email_hash = ''
            nickname = None
            cred_points = None

        params = dict(logout_url=logout_url,
                      login_url=login_url,
                      email_hash=email_hash,
                      nickname=nickname,
                      cred_points=cred_points)

        params.update(kwargs)
        return params


class MainPage(webapp2.RequestHandler):

    @error_catch
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
            

class ResultsHandler(PickThisPageRequest):

    @error_catch
    def get(self):

        image_key = self.request.get("image_key")
        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)

        image, count = get_result_image(img_obj)

        params = self.get_base_params(count=count,
                                      image=image,
                                      img_obj=img_obj)

        template = env.get_template("results.html")
        html = template.render(params)

        self.response.write(html)


class AboutHandler(PickThisPageRequest):
    @error_catch
    def get(self):
        template_params = self.get_base_params()
        template = env.get_template('about.html')
        html = template.render(template_params)
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
    def get(self, user, id=None):

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
        img_objs = ImageObject.all().ancestor(db_parent).fetch(1000)

        template = env.get_template('choose.html')

        params = self.get_base_params(img_objs=img_objs,
                                      upload_url=upload_url,
                                      user_id=user_id
                                      )
        html = template.render(params)

        self.response.write(html)

    @error_catch
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
                             parent=db_parent,
                             user=user,
            user_id=user.user_id())

        new_db.width = new_db.size[0]
        new_db.height = new_db.size[1]
        
        new_db.put()

        self.redirect('/add_image?image_key=' +
                      str(new_db.id))
        
        
class AddImageHandler(PickThisPageRequest):

    @error_catch
    @authenticate
    def get(self, user):

        image_key = self.request.get("image_key")

        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)
        
        template_params = self.get_base_params()
        template_params.update(img_obj=img_obj,
                               image_key=image_key)

        template = env.get_template("add_image.html")
        html = template.render(template_params)
        self.response.write(html)

    @error_catch
    @authenticate
    def post(self, user):

        image_key = self.request.get("image_key")

        title = self.request.get("title")
        description = self.request.get("description")
        challenge = self.request.get("challenge")
        pickstyle = self.request.get("pickstyle")
        permission = self.request.get("permission")
        rightsholder = self.request.get("rightsholder")

        if not rightsholder:
            rightsholder = user.nickname()

        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)

        img_obj.width = img_obj.size[0]
        img_obj.height = img_obj.size[1]

        img_obj.title = title
        img_obj.description = description
        img_obj.challenge = challenge
        img_obj.pickstyle = pickstyle
        img_obj.permission = permission
        img_obj.rightsholder = rightsholder
        img_obj.user = user
        img_obj.user_id = user.user_id()

        # Seems like I have to do this to instantiate properly.
        # I thought that's what default=[] is for.
        #img_obj.interpreters = ['default_user']

        img_obj.put()

        self.redirect('/')
        
