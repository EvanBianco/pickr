import webapp2
from jinja2 import Environment, FileSystemLoader
from os.path import dirname, join
import os
import json
import base64
import hashlib
import StringIO
from google.appengine.api import users

import numpy as np
if not os.environ.get('SERVER_SOFTWARE','').startswith('Development'):
    import PIL
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    #from scipy.ndimage.morphology import grey_dilation
    import Image
    local = False
else:
    local = True

from lib_db import SeismicObject, PickrParent

# Jinja2 environment to load templates.
env = Environment(loader=FileSystemLoader(join(dirname(__file__),
                                               'templates')))

# Data store set up.
db_parent = PickrParent.all().get()
if not db_parent:
    db_parent = PickrParent()
    db_parent.put()


class CommentHandler(webapp2.RequestHandler):

    def get(self):

        index = int(self.request.get("index"))

        data = SeismicObject.all().ancestor(db_parent).sort("-date")
        data = data.fetch(1000)[index]

        self.response.write(json.dumps(data.comments))

    def post(self):

        index = int(self.request.get("index"))
        comment = int(self.request.get("comment"))

        data = SeismicObject.all().ancestor(db_parent).sort("-date")
        data = data.fetch(1000)[index]
        comments = data.comments
        comments.append(comment)

        data.comments = comments
        data.put()

        self.response.write(comment)

      
class VoteHandler(webapp2.RequestHandler):

    def get(self):
        
        index = int(self.request.get("index"))

        data = SeismicObject.all().ancestor(db_parent).order("-date")
        data = data.fetch(1000)[index]

        self.response.write(data.votes)
        
        
    def post(self):

        index = int(self.request.get("index"))
        vote = int(self.request.get("vote"))

        data = SeismicObject.all().ancestor(db_parent).order("-date")
        data = data.fetch(1000)[index]


        if vote > 0:
            vote = 1
        else:
            vote =-1
        
        data.votes += vote

        data.put()
        
        self.response.write(data.votes)
 

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

            self.redirect('/pickr')
            

class ResultsHandler(webapp2.RequestHandler):

    def get(self):

        # connect the dots using one dimensional linear interpretation: np.interp()
        def regularize(xarr, yarr, pxi, pxf):
            # connect the dots of the horizon spanning the image
            # pxi : is the first x pos. 
            # pyi : is the first y pos., and so on
            horx = np.arange(pxi,pxf+1)
            hory = np.interp(horx, xarr, yarr)
            return horx, hory
        
        # append all horizons into one big file
        all_picks_x = np.array([])
        all_picks_y = np.array([])
        
        data = SeismicObject().all().fetch(1000)
        
        count = len(data)

        if not local:
            
            fig = plt.figure(figsize=(15,8))
            ax = fig.add_axes([0,0,1,1])
        
            # Load the image to a variable
            im = Image.open('brazil_ang_unc.png')
            px, py = im.size
            
        
            # plot the seismic image first
            # im = plt.imshow(im)
            # Make a modified version of rainbow colormap with some transparency
            # in the bottom of the colormap.
            hot = cm.hot
            hot.set_under(alpha = 0.0)  #anything that has value less than 0.5 goes transparent
            
            for user in data:
                try:
                    picks = np.array(json.loads(user.picks))
                    hx, hy = regularize(picks[:,0], picks[:,1], pxi, pyf)
                    all_picks_x = np.concatenate((all_picks_x,hx))
                    all_picks_y = np.concatenate((all_picks_y,hy))
                    ax.plot(picks[:,0], picks[:,1], 'g-', alpha=0.5, lw=2)

                    m = 1
                    
                    x1, x2 =  np.amin(all_picks_x), np.amax(all_picks_x)
                    y1, y2 = np.amin(all_picks_y),np.amax(all_picks_y)

                    heat_extent_im = [x1,x2,y2,y1] #flip extents of heatmap for image plot
                    # do 2d histogram to display heatmap
                    binsizex = m
                    binsizey = m
                    heatmap, yedges, xedges = np.histogram2d(all_picks_y, all_picks_x, 
                                                            bins= ((y2-y1)/binsizey,(x2-x1)/binsizex),
                                                            range =np.array([[y1, y2],[x1, x2]])
                                                            )

                    # do dilation of picks in heatmap
                    from mmorph import dilate
                    n = 3 #should be odd integer
                    B = np.array((n,n)).astype(int)
                    heatmap_dil = dilate(heatmap, B=B)
                
                    #fig = plt.figure(figsize=(15,8))
                    #ax = fig.add_axes([0, 0, 1, 1])
                    heatim = ax.imshow(heatmap_dil,
                                       cmap=cm.hot, 
                                       extent=heat_extent_im,
                                       alpha=0.75)
                    heatim.set_clim(0.5, np.amax(heatmap))
                    ax.set_ylim((py,0))
                    ax.set_xlim((0,px))
                    #ax.invert_yaxis()
                    ax.set_xticks([])
                    ax.set_yticks([])
                    ax.set_frame_on(False)
                except:
                    pass
                
            output = StringIO.StringIO()
            plt.savefig(output)
            image = base64.b64encode(output.getvalue())

            user = users.get_current_user()

            # User should exist, so this should fail otherwise.
            logout_url = users.create_logout_url('/')
            login_url = None
            email_hash = hashlib.md5(user.email()).hexdigest()

            template = env.get_template("results.html")
            html = template.render(count=count,
                                   logout_url=logout_url,
                                   email_hash=email_hash,
                                   image=image)

            self.response.write(html)
            

        else:

            with open("alaska.b64", "r") as f:
                image = f.read()
                
            user = users.get_current_user()

            # User should exist, so this should fail otherwise.
            logout_url = users.create_logout_url('/')
            login_url = None
            email_hash = hashlib.md5(user.email()).hexdigest()
            
            template = env.get_template("results.html")
            html = template.render(count=count,
                                   logout_url=logout_url,
                                   email_hash=email_hash,
                                   image=image)
                
            self.response.write(html)

        # Make composite image


class AboutHandler(webapp2.RequestHandler):

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

        # Write the page.
        template = env.get_template('about.html')
        html = template.render(logout_url=logout_url,
                               login_url=login_url,
                               email_hash=email_hash)
        self.response.write(html)


class TermsHandler(webapp2.RequestHandler):

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

        # Write the page.
        template = env.get_template('terms.html')
        html = template.render(logout_url=logout_url,
                               login_url=login_url,
                               email_hash=email_hash)

        self.response.write(html)


class PickerHandler(webapp2.RequestHandler):

    def get(self):

        user = users.get_current_user()

        # User should exist, so this should fail otherwise.
        logout_url = users.create_logout_url('/')
        login_url = None
        email_hash = hashlib.md5(user.email()).hexdigest()

        # Write the page.
        template = env.get_template('pickpoint.html')
        html = template.render(logout_url=logout_url,
                               login_url=login_url,
                               email_hash=email_hash)

        self.response.write(html)


## class UploadHandler(blobstore_handlers.BlobstoreUploadHandler,
##                     webapp2.RequestHandler):

##     def post(self):

##         upload_file = self.get_uploads()
##         blob_info = upload_files[0]

##         # Read the image file
##         reader = blobstore.BlobReader(blob_info.key())

##         im = Image.open(reader, 'r')
##         im = im.convert('RGB').resize((350,350))

##         output = StringIO.StringIO()
##         im.save(output, format='PNG')

##         bucket = '/pickr_bucket/'
##         output_filename = (bucket +'/2' + str(time.time()))

##         gcsfile = gcs.open(output_filename, 'w')
##         gcsfile.write(output.getvalue())

##         output.close()
##         gcsfile.close()

##         # Make a blob reference
##         bs_file = '/gs' + output_filename
##         output_blob_key = blobstore.create_gs_key(bs_file)

##         name = self.request.get("name")
##         description = self.request.get("description")

##         new_db = SeismicObject(name=name, description=description,
##                                image=output_blob_key)

##         new_db.put()

##         self.redirect('/')
               

class PickHandler(webapp2.RequestHandler):

    def get(self):

        user = users.get_current_user()
        if self.request.get("user_picks"):
            data = \
              SeismicObject.all().ancestor(db_parent).filter("user =",
                                                             user).get()

            if data:
                picks = data.picks
            else:
                picks = json.dumps([])
            self.response.write(picks)
            return
        
        if self.request.get("all"):
            data = SeismicObject.all().fetch(1000)

            picks = [i.picks for i in data]
            self.response.write(data)
            return

        if self.request.get("pick_index"):

            data = SeismicObject.all().ancestor(db_parent)
            data = data.order("-date").fetch(1000)

            index = int(self.request.get("pick_index"))

            self.response.write(data[index].picks)
            return

    def post(self):

        point = (int(self.request.get("x")),
                 int(self.request.get("y")))

        user = users.get_current_user()

        if not user:
            self.redirect('/')

        d = SeismicObject.all().ancestor(db_parent).filter("user =",
                                                           user).get()

        if not d:
            d = SeismicObject(picks=json.dumps([point]).encode(),
                              user=user, parent=db_parent,votes=0)
            d.put()
        else:

            picks = json.loads(d.picks)
            picks.append(point)
            d.picks = json.dumps(picks).encode()
            d.put()
        self.response.write("Ok")


    def delete(self):

        user = users.get_current_user()

        data = \
          SeismicObject.all().ancestor(db_parent).filter("user =",
                                                         user).get()

        points = json.loads(data.picks)

        if self.request.get("clear"):
            data.delete()
            value = []
            
        elif self.request.get("undo"):
            
            value = points.pop()
            data.picks = json.dumps(points).encode()
            data.put()
                 
        self.response.write(json.dumps(value))


## class AddImageHandler(webapp2.RequestHandler):

##     def get(self):

##         upload_url = blobstore.create_upload_url('/upload')

##         template = env.get_template("new_image.html")

##         html = template.render(upload_url=upload_url))
##         self.response.write(html)
  

# This is the app.  
app = webapp2.WSGIApplication([
    ('/', MainPage),
    #('/upload', UploadModel),
    #('/new_image', AddImageHandler),
    ('/about', AboutHandler),
    ('/update_pick', PickHandler),
    ('/pickr', PickerHandler),
    ('/terms', TermsHandler),
    ('/results', ResultsHandler),
    ('/comment', CommentHandler),
    ('/vote', VoteHandler)],
    debug=True)
