
import numpy as np
import StringIO, json, base64

from lib_db import Picks, ImageObject, User, Vote

from google.appengine.api import images
from google.appengine.ext import blobstore

# For image manipulation
from PIL import Image
from mmorph import dilate, sedisk


def interpolate(x_in, y_in):
    """
    For line interpretations.
    Connect the dots of each interpretation.
    
    """


    # Check difference in x and in y, so we can
    # interpolate in the direction with the most range

    x_range = np.arange(np.amin(x_in), np.amax(x_in)+1)
    y_range = np.arange(np.amin(y_in), np.amax(y_in)+1)

    # x_out = x_range
    # y_out = np.interp(x_out, x_in, y_in)


    if x_range.size >= y_range.size:
        x_out = x_range
        y_out = np.interp(x_out, x_in, y_in)
    else:
        y_out = y_range
        x_out = np.interp(y_out, y_in, x_in)

    return x_out.astype(int), y_out.astype(int)

    
def normalize(a, newmax):
    """
    Normalize the values of an
    array a to some new max.
    
    """
    return (float(newmax) * a) / np.amax(a)


def get_result_image(img_obj):
    """
    Takes an image, gets its interpretations, and makes a
    new image that shows all the interpretations concatenated.
    Maps a 'heatmap' colourbar to the result.

    Returns the new 'heatmap' image,
    plus a count of interpretations.
    
    """
    # Read the interpretations for this image.
    data = Picks.all().ancestor(img_obj).fetch(1000)
    
    # Get the dimensions.
    w, h = img_obj.width, img_obj.height
    avg = (w + h) / 2.

    # Make an 'empty' image for all the results. 
    heatmap_image = np.zeros((h, w))

    # Now loop over the interpretations and sum into that empty image.
    for user in data:

        # Make a new image for this interpretation.
        user_image = np.zeros((h, w))

        # Get the points.
        picks = np.array(json.loads(user.picks))

        print picks

        if img_obj.pickstyle == 'polygons':
            picks = np.append(picks, picks[0]).reshape(picks.shape[0]+1, picks.shape[1])

        # Sort on x values.
        #picks = picks[picks[:,0].argsort()]

        # This needs refactoring!

        # Deal with the points, and set the
        # radius of the disk structuring element.
        if img_obj.pickstyle != 'points':
            for i in range(picks.shape[0] - 1):

                xpair = picks[i:i+2,0]

                if xpair[0] > xpair[1]:
                    xpair = xpair[xpair[:].argsort()]
                    xrev = True
                else:
                    xrev = False

                ypair = picks[i:i+2,1]

                print " ++ IN THE LOOP ++ "
                print xpair, ypair

                if ypair[0] > ypair[1]:
                    ypair = ypair[ypair[:].argsort()]
                    yrev = True
                else:
                    yrev = False

                # Do the interpolation
                x, y = interpolate(xpair, ypair)

                if xrev: # then need to unreverse...
                    x = x[::-1]
                if yrev: # then need to unreverse...
                    y = y[::-1]

                # Build up the image
                user_image[(y, x)] = 1.
            
            n = np.ceil(avg / 300.).astype(int) 

        else:
            x, y = picks[:,0], picks[:,1]
            user_image[(y, x)] = 1.

            n = np.ceil(avg / 150.).astype(int) # The radius of the disk structuring element

        # Make line into image.        
        #user_image[(y, x)] = 1.

        # Dilate this image.
        dilated_image = dilate(user_image.astype(int),
                               B=sedisk(r=n))

        # Add it to the running summed image.
        heatmap_image += dilated_image

    # Normalize the heatmap from 0-255 for making an image.
    # More muted version: Subtract 1 first to normalize to
    # the non-zero data only.
    heatmap_norm = normalize(heatmap_image, 255)
    
    # Make the RGB channels.
    r = np.clip((2 * heatmap_norm), 0, 255)
    g = np.clip(((3 * heatmap_norm) - 255), 0, 255)
    b = np.clip(((3 * heatmap_norm) - 510), 0, 255)

    # Make the A (opacity) channel, setting all the non-picked areas
    # to transparent.
    opacity = 1.0
    a = opacity * 255 * np.ones_like(heatmap_norm)
    # Set everything corresponding to zero data to transparent.
    a[heatmap_image==0] = 0 

    # Make the 4-channel image from an array.
    im = np.dstack([r, g, b, a])
    im_out = Image.fromarray(im.astype('uint8'), 'RGBA')

    # Save out into file-like.
    output = StringIO.StringIO()
    im_out.save(output, 'png')
    
    return base64.b64encode(output.getvalue())

def statistics():

    stats = {"user_count": User.all().count(),
             "image_count": ImageObject.all().count(),
             "pick_count":  Picks.all().count(),
             "vote_count": Vote.all().count()}

    return stats
    


 

