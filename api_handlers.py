import webapp2
from lib_db import ImageObject, Picks, Vote

from constants import db_parent

import json

from google.appengine.api import users

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
            self.error(500)
            
    return call_and_catch


class CommentHandler(webapp2.RequestHandler):

    @error_catch
    def get(self):

        index = int(self.request.get("index"))

        data = ImageObject.all().ancestor(db_parent).sort("-date")
        data = data.fetch(1000)[index]

        self.response.write(json.dumps(data.comments))

    @error_catch
    @authenticate
    def post(self, user):

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

    @error_catch
    def get(self):

        self.response.headers["Content-Type"] = "application/json"
        

        index = int(self.request.get("index"))
        image_key = int(self.request.get("image_key"))

    
        img = ImageObject.get_by_id(image_key, parent=db_parent)
        picks = Picks.all().ancestor(img).order("date").fetch(1000)
        picks = picks[index]

        votes = picks.votes

        user = users.get_current_user()

        
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
        

    @error_catch
    @authenticate
    def post(self, user):

        self.response.headers["Content-Type"] = "application/json"

        index = int(self.request.get("index"))
        update_vote = int(self.request.get("vote"))
        img_key = int(self.request.get("image_key"))
        user = users.get_current_user()

        img = ImageObject.get_by_id(img_key,
                                    parent=db_parent)
        picks = Picks.all().ancestor(img).order("date").fetch(1000)

        # Prevent self voting
        if user == picks[index].user:
            update_vote = 0
            
        elif update_vote > 0:
            update_vote = 1
        else:
            update_vote = -1

        vote = Vote.all().ancestor(picks[index]).filter("user =",
                                                        user).get()
        if vote is None:
            vote = Vote(user=user, value=update_vote,
                        parent=picks[index])
        else:
            # reset if they try to set to the same vote
            if vote.value == update_vote:
                vote.value = 0
            else:
                vote.value = update_vote

        vote.put()
        
        data = {"votes": picks[index].votes,
                "user_choice": vote.value}
        
        self.response.write(json.dumps(data))
 

class PickHandler(webapp2.RequestHandler):

    @error_catch
    def get(self):

        user = users.get_current_user()
        image_key = self.request.get("image_key")
        img_obj = ImageObject.get_by_id(int(image_key),
                                        parent=db_parent)

        if self.request.get("user_picks"):
   
            data_obj = Picks.all().ancestor(img_obj)
            data = data_obj.filter("user =", user).get()
            
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

    @error_catch
    @authenticate
    def post(self, user):

        point = (int(self.request.get("x")),
                 int(self.request.get("y")))

        image_key = self.request.get("image_key")

        img_obj = ImageObject.get_by_id(int(image_key),
                                          parent=db_parent)
        
        picks = Picks.all().ancestor(img_obj)
        picks = picks.filter("user =", user).get()

        if not picks:
            # Then the user has not picked
            # this image before so start
            # some picks for this user.
            picks = Picks(user=user,
                          picks=json.dumps([point]).encode(),
                          parent=img_obj)
            picks.put()
            
            # In this case we also need to 
            # make a note of this user
            # interpreting this image.
            img_obj.interpreters.append(user.user_id())
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
    def delete(self, user):

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

            # Also remove the user from the list of 
            # interpreters of this image.
            img_obj.interpreters.remove(user.user_id())
            img_obj.put()
            
        elif self.request.get("undo"):
            
            value = points.pop()
            data.picks = json.dumps(points).encode()
            data.put()
                 
        self.response.write(json.dumps(value))
