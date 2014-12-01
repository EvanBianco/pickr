import webapp2
from page_handlers import *
from api_handlers import *



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
    ('/vote', VoteHandler),
    ('/image', ImageHandler),
    ('BlobURL', BlobURLHandler),
    ('/err', ErrorHandler),
    ('/.*', ErrorHandler)],
    debug=True)
