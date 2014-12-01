$(function() {
    pickDrawing.setup('image-div');
/* I don't think we need to do this, 
   because there are no picks to load.
   It raises a JS error as a result,
   but doesn't do any harm.
   
    pickDrawing.load({ user_picks: 1,
		       image_key: image_key});

*/
    $('#image-div').click(function(e) {
        var imageX = e.pageX - this.offsetLeft;
        var imageY = e.pageY - this.offsetTop - 2;
        var point = { x: imageX, y: imageY };
        pickDrawing.clickPoint(point);
    });
    
    $('#clear-button').click(function(){
	$.ajax("/update_pick?clear=1&image_key=" + image_key,
            {
	        type: "DELETE",
            success: function(){
		        pickDrawing.clear();
            }
	   });
    });

    $('#undo-button').click(function(){
        $.ajax("/update_pick?undo=1&image_key="+image_key, {
            type: "DELETE",
            dataType: "json",
            success: function(p){
		        pickDrawing.removePoint({x: p[0], y: p[1]});
		     }
        });
    });
});
