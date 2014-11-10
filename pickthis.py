
import numpy as np
import StringIO, json, base64

from lib_db import SeismicPicks

from google.appengine.api import images
from google.appengine.ext import blobstore

# For image manipulation
from PIL import Image
from mmorph import dilate, sedisk


def regularize(xarr, yarr):
    """
    For line interpretations.
    Connect the dots of each interpretation.
    
    """
    horx = np.arange(np.amin(xarr), np.amax(xarr))
    hory = np.interp(horx, xarr, yarr)
    return horx.astype(int), hory.astype(int)

    
def normalize(arr, newmax):
    """
    Normalize the values of an array to some new max.
    
    """
    return (float(newmax) * arr) / np.amax(arr)


def get_result_image(img_obj):
    """
    Takes an image, gets its interpretations, and makes a
    new image that shows all the interpretations concatenated.
    Maps a 'heatmap' colourbar to the result.

    Returns the new 'heatmap' image,
    plus a count of interpretations.
    
    """

    # Read the interpretations for this image.
    data = SeismicPicks.all().ancestor(img_obj).fetch(1000)
    
    # Get the dimensions.
    reader = blobstore.BlobReader(img_obj.image)
    im = Image.open(reader, 'r')
    px, py = im.size

    # DEBUGGING SIZE ISSUE
    # Beware, PIL size gives width x height
    print "im.size:", im.size

    # Get all the interpretations.
    heatmap_image = np.zeros((py,px))
    for user in data:
        user_image = np.zeros((py,px))
        picks = np.array(json.loads(user.picks))
        # line of points (called h for horizon)
        hx, hy = regularize(picks[:,0], picks[:,1])
        # make line into image        
        user_image[(hy,hx)] = 1
        # dilate this image
        r = np.array([[0, py], [0, px]])
        n = np.ceil(py / 500.0).astype(int) # The radius of the disk structuring element
        n = 2
        dilated_image = dilate(user_image.astype(int), B = sedisk(r=n) )
        heatmap_image += dilated_image

    # DEBUGGING SIZE ISSUE
    print "heatmap.shape:", heatmap_image.shape

    # Normalize the heatmap from 0-255 for making an image.
    # We subtract 1 first to normalize to the non-zero data only.
    heatmap_norm = normalize(heatmap_image - 1, 255)
    
    # Make the RGB channels.
    r = np.clip((2 * heatmap_norm), 0, 255)
    g = np.clip(((3 * heatmap_norm) - 255), 0, 255)
    b = np.clip(((3 * heatmap_norm) - 510), 0, 255)

    # Make the A chanel, setting all the non-picked areas to transparent.
    opacity = 1.0 #
    a = opacity * 255 * np.ones_like(heatmap_norm)
    # Set everything corresponding to zero data to transparent.
    a[heatmap_image==0] = 0 

    # Make the 4-channel image from an array.
    x = np.dstack([r, g, b, a])
    im_out = Image.fromarray(x.astype('uint8'), 'RGBA')

    # DEBUGGING SIZE ISSUE
    print "x.shape:", x.shape

    # Save out into file-like.
    output = StringIO.StringIO()
    im_out.save(output, 'png')
    
    # We also need to know the number of interpretations.
    count = len(data)

    return base64.b64encode(output.getvalue()), count
