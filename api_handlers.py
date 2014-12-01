import webapp2
import traceback
import cgi

from lib_db import ImageObject, Picks, Vote, Comment

from constants import db_parent

import json

from google.appengine.api import users
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore

def authenticate(func):
    """
    Wrapper function for methods that require a logged in
    user
    """
    def authenticate_and_call(self, *args, **kwargs):
        user = users.get_current_user()
        if user is None:
            raise Exception
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
            print traceback.format_exc()
            self.error(500)
            
    return call_and_catch


class CommentHandler(webapp2.RequestHandler):


    @error_catch
    @authenticate
    def post(self, user_id):
        
        """
        Users can comment on images, from a simple form on the page.
        Should be no need to handle with a new bit of API, just
        post to this page. 

        """


        image_key = self.request.get("image_key")

 
        
        img_obj = ImageObject.get_by_id(int(image_key), parent=db_parent)

        text = cgi.escape(self.request.get("text"))

        comment = Comment(text=text,
                          user_id=user_id,
                          parent=img_obj)

        # comment.datetime is set automatically

        comment.put()

        # This is fine for now, but we be using AJAX calls and
        # rendering the comments in the browser. Or if we are doing
        # it this way, we should move the code to just post to results
        self.redirect('/results?image_key='+ str(image_key))

 

class ImageHandler(webapp2.RequestHandler):

    @error_catch
    @authenticate
    def delete(self,user_id):

        image_key = self.request.get("image_key")

        image_obj = ImageObject.get_by_id(int(image_key),
                                          parent=db_parent)

        if ((image_obj.user_id == user_id) or
            (users.is_current_user_admin())):

            self.response.headers["Content-Type"] = "application/json"

            if not Picks.all().ancestor(image_obj).get():
                # Then there are no intepretations, so anyone can delete.
                image_obj.delete()
                self.response.write(json.dumps({"success":True}))
            else:
                # There are interpretations.
                if users.is_current_user_admin():
                    # Then you can delete all the same.
                    image_obj.delete()
                    self.response.write(json.dumps({"success":True}))
                else:
                    self.response.write(json.dumps({"interpretations":True}))
            
        else:
            self.error(500)

        
class VoteHandler(webapp2.RequestHandler):

    @error_catch
    @authenticate
    def get(self, user_id):
        """ 
        Request the total number of votes for a particular
        interpreter's interpretation for a given image, and
        the value of the current user's choice.

        E.g. user_id: kwinkunks
             user: test@example.com (interpreter)
             image_key: Brazil.png
             (of course we provide keys, not plain text)

             result:  {"votes": 12,
                       "user_choice": -1
                       }

             So the test@example.com's pick on that image
             has 12 votes total, and kwinkunks voted -1.
 
        """
        self.response.headers["Content-Type"] = "application/json"
        
        interpreter_id = self.request.get("user")
        image_key = int(self.request.get("image_key"))

        # Get the image, and then its picks.
        # Then filter back to the requested
        # interpreter's pick.
        img = ImageObject.get_by_id(image_key, parent=db_parent)
        picks = Picks.all().ancestor(img)
        pick = picks.filter("user_id =", interpreter_id).get()

        # Get the total votes for this pick.
        votes = pick.votes
    
        # Get all the votes for this pick, 
        # then filter back to this user's votes.
        user_votes = Vote.all().ancestor(pick)
        user_vote = user_votes.filter("user_id =",user_id).get()

        # Figure out what this user voted.
        if not user_vote:
            user_choice = 0
        else:
            user_choice = user_vote.value

        # Build a dict to send back.
        data = {"votes": votes,
                "user_choice": user_choice}
    
        self.response.write(json.dumps(data))
        

    @error_catch
    @authenticate
    def post(self, user_id):
        """ 
        Post a change to the total number of votes for a
        particular interpretation for a given
        image, and the value of the current user's choice.

        E.g. user_id: kwinkunks
             user: test@example.com (interpreter)
             image_key: Brazil.png
             vote:-1
             (of course we provide keys, not plain text)

             result:  {"votes": 12,
                       "user_choice": -1
                       }

             So kwinkunks voted -1 on the test@example.com's
             pick on that image, and it now has 12 votes total.
 
        """

        self.response.headers["Content-Type"] = "application/json"

        interpreter_id = self.request.get("user")
        update_vote = int(self.request.get("vote"))
        img_key = int(self.request.get("image_key"))
        user = users.get_current_user()

        img = ImageObject.get_by_id(img_key,
                                    parent=db_parent)

        # Get the image's picks, then filter
        # down to the specified interpreter's pick.
        picks = Picks.all().ancestor(img)
        pick = picks.filter("user_id =", interpreter_id).get()

        # Check if this user is the interpreter; 
        # if not, set a vote value.
        if user_id == interpreter_id:
            update_vote = 0   # A self-vote, not allowed
        elif update_vote > 0:
            update_vote = 1   # An upvote
        else:
            update_vote = -1  # A downvote

        # Get all the votes for this pick, 
        # then filter to this user's vote.
        votes = Vote.all().ancestor(pick)
        vote = votes.filter("user_id =", user_id).get()

        # If this is their first vote, make a new
        # Vote object.
        if vote is None:
            vote = Vote(user_id=user_id,
                        value=update_vote,
                        parent=pick
                       )
        else:
            # We are updating the existing vote;
            # reset if they try to set to the same vote
            if vote.value == update_vote:
                vote.value = 0
            else:
                vote.value = update_vote

        # Write the vote object to the db.
        vote.put()
        
        # Build the dict to send back.
        data = {"votes": pick.votes,
                "user_choice": vote.value}
        
        self.response.write(json.dumps(data))
 

class PickHandler(webapp2.RequestHandler):
    
    @error_catch
    @authenticate
    def get(self, user_id):

        image_key = self.request.get("image_key")
        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent
                                        )

        if self.request.get("all"):
            data = Picks.all().ancestor(img_obj)
            self.response.write(data)
            return

        if self.request.get("user_picks"):
            # Write out the picks belonging to the
            # requesting user.

            data = Picks.all().ancestor(img_obj)
            data = data.filter("user_id =", user_id).get()
            
            if data:
                picks = data.picks
            else:
                picks = json.dumps([])

            self.response.write(picks)
            return
        
        if self.request.get("user"):
            # Write out the picks for a specific user,
            # along with some flags to decide on 
            # display colour (set in pick-drawing.js).

            # Filter out current user's first...
            user_data = Picks.all().ancestor(img_obj).filter("user_id =", user_id).get()

            # Now get the owner's...
            owner_id = img_obj.user_id
            owner_data = Picks.all().ancestor(img_obj).filter("user_id =", owner_id).get()

            # Finally get everyone else's.
            pick_user_id = self.request.get("user")
            other_data = Picks.all().ancestor(img_obj).filter("user_id =", pick_user_id).get()


            # Deal with getting None
            if other_data:
                other_data = json.loads(other_data.picks)
            else:
                other_data = json.loads('[]')

            if owner_data:
                owner_data = json.loads(owner_data.picks)
            else:
                owner_data = json.loads('[]')

            # There should always be user data
            # But maybe not for admins...
            if user_data: 
                user_data = json.loads(user_data.picks)
            else:
                user_data = json.loads('[]')

            # Might as well set owner user 
            # AND current user flags. Display logic
            # is in pick-drawing.js
            # Should no longer need to do this...
            owner, current = False, False
            if (user_id == pick_user_id):
                current = True
            if (owner_id == pick_user_id):
                owner = True

            output = {"data": other_data,
                      "owner_data": owner_data,
                      "user_data": user_data,
                      "owner": owner,
                      "current": current
                      }

            self.response.headers["Content-Type"] = "application/json"
            self.response.write(json.dumps(output))
            return

    @error_catch
    @authenticate
    def post(self, user_id):

        point = (int(self.request.get("x")),
                 int(self.request.get("y")))

        image_key = self.request.get("image_key")

        img_obj = ImageObject.get_by_id(int(image_key),
                                          parent=db_parent)
        
        picks = Picks.all().ancestor(img_obj)
        picks = picks.filter("user_id =", user_id).get()

        if not picks:
            # Then the user has not picked
            # this image before so start
            # some picks for this user.
            picks = Picks(user_id=user_id,
                          picks=json.dumps([point]).encode(),
                          parent=img_obj)
            picks.put()
            img_obj.put()

        else:
            # Then carry on adding picks.
            all_picks = json.loads(picks.picks)
            all_picks.append(point)
            picks.picks = json.dumps(all_picks).encode()
            picks.put()
            
        self.response.write("Ok")

    @error_catch
    @authenticate
    def delete(self, user_id):

        image_key = self.request.get("image_key")

        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)

        data = Picks.all().ancestor(img_obj).filter("user_id =",
                                                    user_id)
        data = data.get()

        points = json.loads(data.picks)

        if self.request.get("clear"):
            data.delete()
            value = []
            img_obj.put()
            
        elif self.request.get("undo"):
            
            value = points.pop()
            data.picks = json.dumps(points).encode()
            data.put()
                 
        self.response.write(json.dumps(value))


class BlobURLHandler(blobstore_handlers.BlobstoreUploadHandler):

    @error_catch
    @authenticate
    def get(self, user_id):

        
        upload_url = blobstore.create_upload_url('/upload')

        self.response.write(upload_url)
